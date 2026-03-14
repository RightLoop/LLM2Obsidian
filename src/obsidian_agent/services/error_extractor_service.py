"""Structured error extraction for smart workflows."""

from __future__ import annotations

import logging
import re

from obsidian_agent.domain.schemas import ErrorCaptureRequest, ErrorObject
from obsidian_agent.services.llm_service import LLMService
from obsidian_agent.utils.slugify import slugify

logger = logging.getLogger(__name__)


class ErrorExtractorService:
    """Extract a structured error object from a user submission."""

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service
        self.last_telemetry: dict[str, object] = {}

    async def extract(self, payload: ErrorCaptureRequest) -> ErrorObject:
        prompt_text = self._compose_input(payload)
        raw = await self.llm_service.run_structured_task(
            instructions=(
                "Return JSON with keys: title, language, error_signature, summary, trigger_mistake, "
                "root_cause, incorrect_assumption, corrective_rule, next_time_checklist, evidence, "
                "related_concepts, tags, confidence. Use Simplified Chinese for every natural-language "
                "field unless a code identifier or standard technical term is clearer in English. "
                "Be specific to this exact submission. Keep the language field as the source language "
                "such as 'c'. The title must describe the concrete mistake, not just the topic area. "
                "trigger_mistake should name the exact wrong move in this question. root_cause should "
                "state the missing distinction. incorrect_assumption should capture the false belief. "
                "corrective_rule should be a short rule the learner can reuse next time. "
                "next_time_checklist must contain 2 to 4 short checklist items."
            ),
            input_text=prompt_text,
        )
        self.last_telemetry = self.llm_service.pop_telemetry()
        if self.last_telemetry:
            logger.info("smart_telemetry task=error_extract telemetry=%s", self.last_telemetry)
        if raw:
            return ErrorObject.model_validate(self._sanitize(raw, payload))
        return self._fallback(payload)

    def _compose_input(self, payload: ErrorCaptureRequest) -> str:
        return (
            f"Title: {payload.title or ''}\n"
            f"Language: {payload.language}\n"
            f"Prompt:\n{payload.prompt}\n\n"
            f"Code:\n{payload.code}\n\n"
            f"User analysis:\n{payload.user_analysis}\n"
        ).strip()

    def _sanitize(self, raw: dict[str, object], payload: ErrorCaptureRequest) -> dict[str, object]:
        fallback = self._fallback(payload)
        return {
            "title": self._clean_sentence(str(raw.get("title") or fallback.title), fallback.title),
            "language": str(raw.get("language") or payload.language or "c"),
            "error_signature": str(raw.get("error_signature") or fallback.error_signature),
            "summary": self._clean_sentence(str(raw.get("summary") or fallback.summary), fallback.summary),
            "trigger_mistake": self._clean_sentence(
                str(raw.get("trigger_mistake") or fallback.trigger_mistake),
                fallback.trigger_mistake,
            ),
            "root_cause": self._clean_sentence(
                str(raw.get("root_cause") or fallback.root_cause),
                fallback.root_cause,
            ),
            "incorrect_assumption": self._clean_sentence(
                str(raw.get("incorrect_assumption") or fallback.incorrect_assumption),
                fallback.incorrect_assumption,
            ),
            "corrective_rule": self._clean_sentence(
                str(raw.get("corrective_rule") or fallback.corrective_rule),
                fallback.corrective_rule,
            ),
            "next_time_checklist": self._clean_list(
                self._coerce_list(raw.get("next_time_checklist")) or fallback.next_time_checklist
            ),
            "evidence": self._clean_list(self._coerce_list(raw.get("evidence")) or fallback.evidence),
            "related_concepts": self._normalize_concepts(
                self._coerce_list(raw.get("related_concepts")) or fallback.related_concepts
            ),
            "tags": self._normalize_tags(self._coerce_list(raw.get("tags")) or fallback.tags),
            "confidence": self._coerce_confidence(raw.get("confidence")),
        }

    def _fallback(self, payload: ErrorCaptureRequest) -> ErrorObject:
        signature = self._infer_signature(payload.prompt, payload.code, payload.user_analysis)
        concepts = self._infer_related_concepts(payload.prompt, payload.code, payload.user_analysis)
        return ErrorObject(
            title=self._normalize_title(payload.title or self._title_for_signature(signature)),
            language=payload.language or "c",
            error_signature=signature,
            summary=self._build_summary(signature, payload),
            trigger_mistake=self._build_trigger_mistake(signature, payload),
            root_cause=self._build_root_cause(signature, concepts),
            incorrect_assumption=self._build_incorrect_assumption(signature, concepts),
            corrective_rule=self._build_corrective_rule(signature, concepts),
            next_time_checklist=self._build_checklist(signature, concepts),
            evidence=self._build_evidence(payload) or ["题面和自我分析里已经暴露出这次判断失误的直接线索。"],
            related_concepts=concepts,
            tags=self._normalize_tags(["c-language", signature, *concepts[:2]]),
            confidence=0.55,
        )

    def _infer_title(self, prompt: str) -> str:
        first_line = prompt.strip().splitlines()[0] if prompt.strip() else "C language error"
        return first_line[:80]

    def _infer_signature(self, prompt: str, code: str, analysis: str) -> str:
        haystack = f"{prompt}\n{code}\n{analysis}".lower()
        if "sizeof" in haystack and any(
            token in haystack for token in ("strlen", "string length", "字符串长度", "可见长度")
        ):
            return "sizeof-vs-strlen"
        if "&arr" in haystack and "arr" in haystack:
            return "arr-vs-address-of-array"
        if "char *" in haystack and "char[" in haystack:
            return "char-pointer-vs-char-array"
        if ("function" in haystack and "parameter" in haystack) or "形参" in haystack:
            return "function-parameter-decay"
        if "\\0" in haystack or "null terminator" in haystack or "字符串结尾" in haystack:
            return "missing-null-terminator"
        if any(token in haystack for token in ("len + 1", "malloc(len)", "malloc(strlen", "少分配一个字节")):
            return "string-allocation-off-by-one"
        if any(token in haystack for token in ("return local", "dangling", "悬空指针", "lifetime")):
            return "dangling-pointer-lifetime"
        if any(token in haystack for token in ("padding", "alignment", "对齐", "结构体布局")):
            return "struct-layout-alignment"
        if any(token in haystack for token in ("pointer arithmetic", "off by one", "越过末尾", "p + len")):
            return "pointer-arithmetic-off-by-one"
        if "array" in haystack and "pointer" in haystack:
            return "array-pointer-decay"
        return slugify(self._infer_title(prompt))

    def _infer_related_concepts(self, prompt: str, code: str, analysis: str) -> list[str]:
        haystack = f"{prompt}\n{code}\n{analysis}".lower()
        concepts: list[str] = []
        pairs = [
            ("sizeof", "sizeof"),
            ("strlen", "strlen"),
            ("pointer", "pointer"),
            ("array", "array"),
            ("decay", "array-decay"),
            ("char *", "char-pointer"),
            ("char[", "char-array"),
            ("parameter", "function-parameter"),
            ("&arr", "address-of-array"),
            ("\\0", "null-terminator"),
            ("alignment", "memory-alignment"),
            ("padding", "struct-padding"),
            ("lifetime", "pointer-lifetime"),
        ]
        for needle, label in pairs:
            if needle in haystack and label not in concepts:
                concepts.append(label)
        if "字符串" in haystack and "null-terminator" not in concepts:
            concepts.append("null-terminator")
        return self._normalize_concepts(concepts or ["pointer-semantics"])

    def _build_summary(self, signature: str, payload: ErrorCaptureRequest) -> str:
        title = self._title_for_signature(signature)
        prompt_line = payload.prompt.strip().splitlines()[0].strip() if payload.prompt.strip() else ""
        if prompt_line:
            return f"这次错题的关键不在于记忆某个结论，而在于把“{title}”相关的判断标准混在了一起：{prompt_line[:90]}"
        return f"这次错题暴露出“{title}”上的判断边界不清。"

    def _build_trigger_mistake(self, signature: str, payload: ErrorCaptureRequest) -> str:
        mapping = {
            "sizeof-vs-strlen": "在读题或读代码时，直接把 sizeof 的结果当成字符串当前可见字符数。",
            "arr-vs-address-of-array": "把 arr 和 &arr 当成同一种指针值或同一种类型来理解。",
            "char-pointer-vs-char-array": "把 char* 和 char[] 当成完全等价的对象来推理。",
            "function-parameter-decay": "进入函数后仍按“原数组”去理解形参，而没有意识到它已经退化为指针。",
            "missing-null-terminator": "构造字符串时只关心可见字符，没有为结尾的 \\0 留出位置或写入它。",
            "string-allocation-off-by-one": "为字符串分配空间时只按字符数计算，漏掉了结尾 \\0 的一个字节。",
            "dangling-pointer-lifetime": "把局部对象地址或已失效内存继续当成可安全使用的有效指针。",
            "struct-layout-alignment": "按成员表面顺序估算大小，没有把对齐和填充字节算进去。",
            "pointer-arithmetic-off-by-one": "做指针偏移时越过了合法边界，或把尾后一位当成可解引用位置。",
            "array-pointer-decay": "把数组名和指针变量在所有上下文里都当成同一回事。",
        }
        return mapping.get(signature, f"这次提交里最直接的错误动作是：{payload.prompt.strip()[:90]}")

    def _build_root_cause(self, signature: str, concepts: list[str]) -> str:
        mapping = {
            "sizeof-vs-strlen": "没有区分“对象占用的字节数”和“C 字符串逻辑长度”这两个完全不同的量。",
            "arr-vs-address-of-array": "没有区分“数组首元素地址”与“整个数组对象的地址”，也没有区分对应类型。",
            "char-pointer-vs-char-array": "没有分清“指针变量保存地址”和“数组对象自带存储空间”这两个层面。",
            "function-parameter-decay": "没有掌握数组作为函数参数时会退化成指针这一语义规则。",
            "missing-null-terminator": "没有把“字符串必须以 \\0 终止”当成内存布局的一部分去思考。",
            "string-allocation-off-by-one": "字符串内存模型不扎实，忽略了终止符也是必须存储的内容。",
            "dangling-pointer-lifetime": "对象生命周期意识薄弱，不清楚地址值存在不代表对象仍然有效。",
            "struct-layout-alignment": "缺少结构体布局与对齐规则的内存视角，只按直觉累计成员大小。",
            "pointer-arithmetic-off-by-one": "边界意识不强，没有严格区分“可指向的位置”和“可解引用的位置”。",
            "array-pointer-decay": "没有建立“数组、指针、退化”三者在不同上下文下的边界规则。",
        }
        primary = concepts[0] if concepts else "C 语义边界"
        return mapping.get(signature, f"根因是没有真正建立“{primary}”相关的语义边界。")

    def _build_incorrect_assumption(self, signature: str, concepts: list[str]) -> str:
        mapping = {
            "sizeof-vs-strlen": "错误地认为 sizeof 得到的就是字符串当前内容的长度。",
            "arr-vs-address-of-array": "错误地认为 arr 与 &arr 不仅值看起来接近，类型和含义也一样。",
            "char-pointer-vs-char-array": "错误地认为 char* 和 char[] 可以在任何语境下互换理解。",
            "function-parameter-decay": "错误地认为数组传参后仍然保留原数组大小信息。",
            "missing-null-terminator": "错误地认为只要字符内容对了，字符串就算构造完成。",
            "string-allocation-off-by-one": "错误地认为 strlen 返回的字符数就是所需总字节数。",
            "dangling-pointer-lifetime": "错误地认为地址没变就还能继续使用那块对象。",
            "struct-layout-alignment": "错误地认为结构体大小只等于各成员 sizeof 直接相加。",
            "pointer-arithmetic-off-by-one": "错误地认为尾后一位也可以像正常元素一样解引用。",
            "array-pointer-decay": "错误地认为数组名天然就是普通指针变量。",
        }
        primary = concepts[0] if concepts else "相关概念"
        return mapping.get(signature, f"错误地把“{primary}”和相邻概念视为同一回事。")

    def _build_corrective_rule(self, signature: str, concepts: list[str]) -> str:
        mapping = {
            "sizeof-vs-strlen": "先问自己“我在算的是存储空间，还是字符串逻辑长度”，再决定用 sizeof 还是 strlen。",
            "arr-vs-address-of-array": "看到 arr 和 &arr 时，先分别写出它们的类型，再继续判断表达式含义。",
            "char-pointer-vs-char-array": "先确认对象本体是什么：是“保存地址的变量”，还是“真正存储字符的数组”。",
            "function-parameter-decay": "函数形参里的数组写法先按“指针”理解，不要默认还能得到原数组大小。",
            "missing-null-terminator": "只要要表示 C 字符串，就必须显式检查末尾是否留有并写入 \\0。",
            "string-allocation-off-by-one": "给字符串分配空间时，始终按“可见字符数 + 1”计算。",
            "dangling-pointer-lifetime": "每次保留地址前，先确认被指对象的生命周期是否覆盖后续使用点。",
            "struct-layout-alignment": "算结构体大小时，不要跳过对齐与 padding，先按布局规则推一遍。",
            "pointer-arithmetic-off-by-one": "指针移动后先判断是否仍在可解引用范围内，再读写。",
            "array-pointer-decay": "先判断当前上下文是否发生数组退化，再决定能否按指针语义处理。",
        }
        primary = concepts[0] if concepts else "这个概念"
        return mapping.get(signature, f"下次遇到类似题时，先显式写出“{primary}”与相邻概念的区别再作答。")

    def _build_checklist(self, signature: str, concepts: list[str]) -> list[str]:
        mapping = {
            "sizeof-vs-strlen": [
                "先确认题目问的是字节数还是字符串长度",
                "看到数组或指针时分清 sizeof 的作用对象",
                "涉及字符串时单独检查是否受 \\0 影响",
            ],
            "arr-vs-address-of-array": [
                "先写出 arr 的类型",
                "再写出 &arr 的类型",
                "比较两者指向的对象层级是否相同",
            ],
            "char-pointer-vs-char-array": [
                "判断对象是否自带存储空间",
                "判断当前变量保存的是内容还是地址",
                "不要在未确认前直接互换推理",
            ],
            "function-parameter-decay": [
                "进入函数后先把数组形参当指针看",
                "不要在形参里用 sizeof 推原数组长度",
                "需要长度时单独传参",
            ],
            "missing-null-terminator": [
                "确认是否要构造合法 C 字符串",
                "检查结尾是否预留 \\0",
                "检查拷贝或拼接后终止符是否仍然存在",
            ],
            "string-allocation-off-by-one": [
                "先算可见字符数",
                "再额外加上终止符一个字节",
                "分配后再检查写入上界",
            ],
            "dangling-pointer-lifetime": [
                "确认被指对象在使用点前没有结束生命周期",
                "不要返回局部变量地址",
                "不要继续使用已释放内存",
            ],
            "struct-layout-alignment": [
                "列出每个成员大小和对齐要求",
                "按顺序计算 padding",
                "最后再处理整体对齐",
            ],
            "pointer-arithmetic-off-by-one": [
                "先标出合法起点和尾后一位",
                "区分可比较位置与可解引用位置",
                "偏移后先做边界检查",
            ],
            "array-pointer-decay": [
                "先判断当前语境是否发生数组退化",
                "区分数组对象和指针变量",
                "涉及 sizeof 时特别小心作用对象",
            ],
        }
        return mapping.get(
            signature,
            [
                "先写出对象本体是什么",
                "再写出表达式实际类型",
                f"最后检查 {concepts[0] if concepts else '关键概念'} 是否被误用",
            ],
        )

    def _build_evidence(self, payload: ErrorCaptureRequest) -> list[str]:
        evidence: list[str] = []
        prompt_line = payload.prompt.strip().splitlines()[0].strip()
        if prompt_line:
            evidence.append(f"题面/描述：{prompt_line[:120]}")
        analysis_line = payload.user_analysis.strip().splitlines()[0].strip()
        if analysis_line:
            evidence.append(f"自我分析：{analysis_line[:120]}")
        code_line = payload.code.strip().splitlines()[0].strip()
        if code_line:
            evidence.append(f"代码线索：{code_line[:120]}")
        return evidence[:3]

    def _title_for_signature(self, signature: str) -> str:
        mapping = {
            "sizeof-vs-strlen": "把 sizeof 当成字符串长度",
            "arr-vs-address-of-array": "混淆 arr 和 &arr 的含义",
            "char-pointer-vs-char-array": "混淆 char* 和 char[]",
            "function-parameter-decay": "忽略数组形参退化为指针",
            "missing-null-terminator": "遗漏字符串结尾的空字符",
            "string-allocation-off-by-one": "字符串分配时漏掉结尾空字符",
            "dangling-pointer-lifetime": "把失效指针当成有效地址继续使用",
            "struct-layout-alignment": "忽略结构体对齐和填充",
            "pointer-arithmetic-off-by-one": "指针偏移时越过合法边界",
            "array-pointer-decay": "把数组和指针在所有语境里混为一谈",
        }
        return mapping.get(signature, signature.replace("-", " "))

    def _normalize_title(self, title: str) -> str:
        cleaned = re.sub(r"\s+", " ", title).strip(" -:：")
        cleaned = cleaned.replace("versus", "vs").replace("VS", "vs")
        return cleaned or "C 语言错题"

    def _clean_sentence(self, value: str, fallback: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            return fallback
        generic_prefixes = (
            "the learner",
            "the submission",
            "this submission",
            "the note",
        )
        if cleaned.lower().startswith(generic_prefixes):
            return fallback
        return cleaned

    def _normalize_concepts(self, concepts: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in concepts:
            label = slugify(item).replace("--", "-").strip("-")
            if not label or label in seen:
                continue
            seen.add(label)
            normalized.append(label)
        return normalized[:5] or ["pointer-semantics"]

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in tags:
            label = slugify(item).strip("-")
            if not label or label in seen:
                continue
            seen.add(label)
            normalized.append(label)
        return normalized[:6] or ["c-language"]

    def _clean_list(self, items: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in items:
            text = re.sub(r"\s+", " ", item).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        return cleaned[:5]

    @staticmethod
    def _coerce_list(value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    @staticmethod
    def _coerce_confidence(value: object) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return 0.55
