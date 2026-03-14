"""Structured error extraction for smart workflows."""

from __future__ import annotations

import logging
import re

from obsidian_agent.domain.schemas import ErrorCaptureRequest, ErrorObject
from obsidian_agent.services.llm_service import LLMService
from obsidian_agent.utils.slugify import slugify

logger = logging.getLogger(__name__)


KNOWN_SIGNATURES = {
    "sizeof-vs-strlen",
    "arr-vs-address-of-array",
    "char-pointer-vs-char-array",
    "function-parameter-decay",
    "missing-null-terminator",
    "string-allocation-off-by-one",
    "dangling-pointer-lifetime",
    "struct-layout-alignment",
    "pointer-arithmetic-off-by-one",
    "array-pointer-decay",
}

TITLE_BY_SIGNATURE = {
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

SUMMARY_BY_SIGNATURE = {
    "sizeof-vs-strlen": "这次错误把“对象占用的字节数”和“字符串逻辑长度”混成了一件事。",
    "arr-vs-address-of-array": "这次错误没有区分首元素地址和整个数组对象地址的对象层级。",
    "char-pointer-vs-char-array": "这次错误把“保存地址的指针变量”和“真实存储字符的数组对象”混成了一件事。",
    "function-parameter-decay": "这次错误忽略了数组作为函数形参时会按指针语义处理。",
    "missing-null-terminator": "这次错误只看到了可见字符，没有把字符串终止符算进内存模型。",
    "string-allocation-off-by-one": "这次错误在字符串容量计算时漏掉了结尾的空字符。",
    "dangling-pointer-lifetime": "这次错误只看到了地址值还在，却没有确认被指对象是否仍然有效。",
    "struct-layout-alignment": "这次错误按成员直觉相加大小，没有从内存布局和对齐规则去判断。",
    "pointer-arithmetic-off-by-one": "这次错误把可比较的位置和可解引用的位置混成了一件事。",
    "array-pointer-decay": "这次错误没有建立数组对象、退化后的指针值、普通指针变量三者的边界。",
}

TRIGGER_BY_SIGNATURE = {
    "sizeof-vs-strlen": "读题时直接把 sizeof 的结果当成字符串当前长度。",
    "arr-vs-address-of-array": "把 arr 和 &arr 当成同一类型、同一层级的地址。",
    "char-pointer-vs-char-array": "把 char* 和 char[] 当成完全等价的对象去推理。",
    "function-parameter-decay": "进入函数后仍把形参 arr 当成原始数组对象。",
    "missing-null-terminator": "构造字符串时只写可见字符，没有检查结尾的 \\0。",
    "string-allocation-off-by-one": "分配空间时只按可见字符数计算，没有额外预留终止符。",
    "dangling-pointer-lifetime": "继续使用已经失效或即将失效对象的地址。",
    "struct-layout-alignment": "估算结构体大小时直接把成员大小相加。",
    "pointer-arithmetic-off-by-one": "偏移到尾后一位后仍继续解引用。",
    "array-pointer-decay": "先把数组名当普通可修改指针，再套用后续结论。",
}

ROOT_CAUSE_BY_SIGNATURE = {
    "sizeof-vs-strlen": "没有区分字节数、元素数和字符串逻辑长度这三个量。",
    "arr-vs-address-of-array": "没有区分首元素地址和整个数组对象地址，对应类型也没有分开看。",
    "char-pointer-vs-char-array": "没有分清“地址变量”和“自带存储空间的数组对象”。",
    "function-parameter-decay": "没有掌握数组传参后会退化为指针这一语义规则。",
    "missing-null-terminator": "没有把 \\0 当成 C 字符串定义的一部分。",
    "string-allocation-off-by-one": "没有把终止符也纳入字符串容量计算。",
    "dangling-pointer-lifetime": "没有把对象生命周期和地址值本身分开理解。",
    "struct-layout-alignment": "缺少从 ABI、对齐和填充角度理解结构体布局的习惯。",
    "pointer-arithmetic-off-by-one": "没有严格区分边界位置、尾后一位和可解引用元素。",
    "array-pointer-decay": "没有区分数组对象本体、退化结果和普通指针变量。",
}

ASSUMPTION_BY_SIGNATURE = {
    "sizeof-vs-strlen": "错误地认为 sizeof 返回的就是当前字符串内容的长度。",
    "arr-vs-address-of-array": "错误地认为 arr 和 &arr 只是写法不同，类型和含义都一样。",
    "char-pointer-vs-char-array": "错误地认为 char* 和 char[] 可以在任何语境下互换理解。",
    "function-parameter-decay": "错误地认为数组传参后仍保留原数组长度信息。",
    "missing-null-terminator": "错误地认为可见字符写完后就已经构成合法 C 字符串。",
    "string-allocation-off-by-one": "错误地认为 strlen 返回的字符数就是所需总字节数。",
    "dangling-pointer-lifetime": "错误地认为地址值还在，就还能安全访问原对象。",
    "struct-layout-alignment": "错误地认为结构体大小等于所有成员 sizeof 直接相加。",
    "pointer-arithmetic-off-by-one": "错误地认为尾后一位和最后一个元素都能像普通元素一样解引用。",
    "array-pointer-decay": "错误地认为数组名天然就是普通指针变量。",
}

RULE_BY_SIGNATURE = {
    "sizeof-vs-strlen": "先问自己在算“字节数”还是“字符串逻辑长度”，再决定用 sizeof 还是 strlen。",
    "arr-vs-address-of-array": "看到 arr 和 &arr 时，先分别写出类型，再继续判断表达式含义。",
    "char-pointer-vs-char-array": "先确认对象本体是地址变量还是实际存储字符的数组。",
    "function-parameter-decay": "进入函数后，数组形参一律先按指针语义理解。",
    "missing-null-terminator": "只要要表示 C 字符串，就显式检查末尾是否预留并写入 \\0。",
    "string-allocation-off-by-one": "给字符串分配空间时，始终按“可见字符数 + 1”计算。",
    "dangling-pointer-lifetime": "保留地址前先确认被指对象的生命周期覆盖后续使用点。",
    "struct-layout-alignment": "算结构体大小时先画布局，再考虑对齐和 padding。",
    "pointer-arithmetic-off-by-one": "偏移后先判断是否仍在可解引用区间内，再读写。",
    "array-pointer-decay": "先判断当前语境是否发生数组退化，再决定能否按指针处理。",
}

CHECKLIST_BY_SIGNATURE = {
    "sizeof-vs-strlen": [
        "先确认题目问的是字节数还是逻辑长度",
        "看到 sizeof 时先写清它作用于谁",
        "涉及字符串时单独检查 \\0 是否参与计算",
    ],
    "arr-vs-address-of-array": [
        "先写出 arr 的类型",
        "再写出 &arr 的类型",
        "确认两者指向的对象层级是否相同",
    ],
    "char-pointer-vs-char-array": [
        "先判断变量保存的是地址还是字符对象本体",
        "确认这段字符存储是否由当前对象拥有",
        "确认当前内容是否允许原地修改",
    ],
    "function-parameter-decay": [
        "进入函数后先按指针理解数组形参",
        "不要在形参里用 sizeof 推原数组长度",
        "需要长度时显式额外传入",
    ],
    "missing-null-terminator": [
        "确认是否要构造合法 C 字符串",
        "检查末尾是否预留 \\0",
        "检查遍历和拷贝是否依赖终止符",
    ],
    "string-allocation-off-by-one": [
        "先算可见字符数",
        "再额外加上终止符一个字节",
        "拷贝前检查目标容量是否足够",
    ],
    "dangling-pointer-lifetime": [
        "确认被指对象在使用点前没有结束生命周期",
        "不要返回局部对象地址",
        "free 后不要继续读取原地址",
    ],
    "struct-layout-alignment": [
        "列出每个成员的大小和对齐要求",
        "按顺序推一遍布局和 padding",
        "最后再看整体对齐后的大小",
    ],
    "pointer-arithmetic-off-by-one": [
        "标出合法起点和尾后一位",
        "区分可比较位置和可解引用位置",
        "偏移后先做边界检查",
    ],
    "array-pointer-decay": [
        "先判断当前语境是否发生数组退化",
        "区分数组对象和指针变量",
        "涉及 sizeof 时特别小心作用对象",
    ],
}

REQUIRED_CONCEPTS = {
    "sizeof-vs-strlen": ["sizeof", "strlen", "null-terminator"],
    "arr-vs-address-of-array": ["array", "pointer", "address-of-array"],
    "char-pointer-vs-char-array": ["char-pointer", "char-array", "string-literal"],
    "function-parameter-decay": ["array-decay", "function-parameter", "sizeof"],
    "missing-null-terminator": ["null-terminator", "char-array", "cstring"],
    "string-allocation-off-by-one": ["strlen", "null-terminator", "memory-allocation"],
    "dangling-pointer-lifetime": ["pointer-lifetime", "stack-memory", "dangling-pointer"],
    "struct-layout-alignment": ["struct-padding", "memory-alignment", "sizeof"],
    "pointer-arithmetic-off-by-one": ["pointer", "pointer-arithmetic", "array-boundary"],
    "array-pointer-decay": ["array", "pointer", "array-decay"],
}

OPTIONAL_CONCEPTS = {
    "sizeof-vs-strlen": {"pointer", "array"},
    "arr-vs-address-of-array": set(),
    "char-pointer-vs-char-array": {"string-literal"},
    "function-parameter-decay": {"array"},
    "missing-null-terminator": {"strlen"},
    "string-allocation-off-by-one": {"char-pointer", "strcpy", "memcpy", "buffer-capacity"},
    "dangling-pointer-lifetime": {"stack-memory", "heap-memory", "use-after-free"},
    "struct-layout-alignment": {"struct-layout"},
    "pointer-arithmetic-off-by-one": {"loop-invariant"},
    "array-pointer-decay": {"multi-dimensional-array", "pointer-level"},
}

CONCEPT_ALIASES = {
    "char*": "char-pointer",
    "char-pointer": "char-pointer",
    "char-array": "char-array",
    "char[]": "char-array",
    "string literal": "string-literal",
    "string-literal": "string-literal",
    "null terminator": "null-terminator",
    "terminator": "null-terminator",
    "\\0": "null-terminator",
    "null-terminator": "null-terminator",
    "address of array": "address-of-array",
    "address-of-array": "address-of-array",
    "&arr": "address-of-array",
    "array decay": "array-decay",
    "array-decay": "array-decay",
    "function parameter": "function-parameter",
    "function-parameter": "function-parameter",
    "pointer lifetime": "pointer-lifetime",
    "pointer-lifetime": "pointer-lifetime",
    "dangling pointer": "dangling-pointer",
    "dangling-pointer": "dangling-pointer",
    "memory alignment": "memory-alignment",
    "memory-alignment": "memory-alignment",
    "struct padding": "struct-padding",
    "struct-padding": "struct-padding",
    "pointer arithmetic": "pointer-arithmetic",
    "pointer-arithmetic": "pointer-arithmetic",
    "array boundary": "array-boundary",
    "array-boundary": "array-boundary",
    "malloc": "memory-allocation",
    "memory allocation": "memory-allocation",
    "memory-allocation": "memory-allocation",
    "stack memory": "stack-memory",
    "stack-memory": "stack-memory",
    "heap memory": "heap-memory",
    "heap-memory": "heap-memory",
    "use after free": "use-after-free",
    "use-after-free": "use-after-free",
    "dynamic array": "dynamic-array",
    "dynamic-array": "dynamic-array",
    "multi dimensional array": "multi-dimensional-array",
    "multi-dimensional-array": "multi-dimensional-array",
    "pointer level": "pointer-level",
    "pointer-level": "pointer-level",
    "struct layout": "struct-layout",
    "struct-layout": "struct-layout",
    "buffer capacity": "buffer-capacity",
    "buffer-capacity": "buffer-capacity",
}

BAD_CONCEPTS = {
    "untitled",
    "title",
    "summary",
    "note",
    "concept",
    "concepts",
    "example",
    "examples",
    "mistake",
    "error",
    "unknown",
    "none",
    "null",
    "vs",
    "c",
    "clang",
    "language",
}


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
                "field unless a code identifier or technical term is clearer in English. Be specific to "
                "this exact submission. The title must describe the concrete mistake, not just the topic. "
                "error_signature must use one of these canonical values when applicable: "
                "sizeof-vs-strlen, arr-vs-address-of-array, char-pointer-vs-char-array, "
                "function-parameter-decay, missing-null-terminator, string-allocation-off-by-one, "
                "dangling-pointer-lifetime, struct-layout-alignment, pointer-arithmetic-off-by-one, "
                "array-pointer-decay. next_time_checklist must contain 2 to 4 short checklist items."
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
        signature = self._canonicalize_signature(str(raw.get("error_signature") or ""), payload)
        if fallback.error_signature in KNOWN_SIGNATURES:
            signature = fallback.error_signature
        elif signature not in KNOWN_SIGNATURES:
            signature = fallback.error_signature
        merged_concepts = self._merge_concepts(
            self._coerce_list(raw.get("related_concepts")),
            fallback.related_concepts,
            signature,
            payload,
        )
        return {
            "title": self._clean_sentence(str(raw.get("title") or fallback.title), fallback.title),
            "language": str(raw.get("language") or payload.language or "c"),
            "error_signature": signature,
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
            "related_concepts": merged_concepts,
            "tags": self._normalize_tags(self._coerce_list(raw.get("tags")) or fallback.tags),
            "confidence": self._coerce_confidence(raw.get("confidence")),
        }

    def _fallback(self, payload: ErrorCaptureRequest) -> ErrorObject:
        signature = self._infer_signature(payload.prompt, payload.code, payload.user_analysis)
        concepts = self._infer_related_concepts(payload.prompt, payload.code, payload.user_analysis)
        return ErrorObject(
            title=self._normalize_title(payload.title or TITLE_BY_SIGNATURE.get(signature, "C 语言错题")),
            language=payload.language or "c",
            error_signature=signature,
            summary=SUMMARY_BY_SIGNATURE.get(signature, "这次错误暴露了对关键语义边界的理解不清。"),
            trigger_mistake=TRIGGER_BY_SIGNATURE.get(signature, "这次直接在关键语义边界上做了错误替换。"),
            root_cause=ROOT_CAUSE_BY_SIGNATURE.get(signature, "没有把相邻概念的判断边界真正分清。"),
            incorrect_assumption=ASSUMPTION_BY_SIGNATURE.get(signature, "错误地把两个相邻概念当成同一件事。"),
            corrective_rule=RULE_BY_SIGNATURE.get(signature, "先写出对象、类型和边界，再下结论。"),
            next_time_checklist=CHECKLIST_BY_SIGNATURE.get(
                signature,
                [
                    "先确认对象本体是什么",
                    "再确认当前表达式的真实类型",
                    "最后检查是否混淆了相邻概念",
                ],
            ),
            evidence=self._build_evidence(payload),
            related_concepts=concepts,
            tags=self._normalize_tags(["c-language", signature, *concepts[:2]]),
            confidence=0.55,
        )

    def _infer_signature(self, prompt: str, code: str, analysis: str) -> str:
        haystack = f"{prompt}\n{code}\n{analysis}".lower()
        if ("function" in haystack and "parameter" in haystack) or "形参" in haystack:
            return "function-parameter-decay"
        mentions_string_length = any(
            token in haystack for token in ("strlen", "string length", "字符串长度", "逻辑长度", "可见长度")
        ) or ("长度" in haystack and any(token in haystack for token in ("char", "字符串", '"')))
        if "sizeof" in haystack and '"' in haystack and ("char" in haystack or "字符串" in haystack):
            return "sizeof-vs-strlen"
        if "sizeof" in haystack and mentions_string_length:
            return "sizeof-vs-strlen"
        if "&arr" in haystack and "arr" in haystack:
            return "arr-vs-address-of-array"
        if "char *" in haystack and ('"' in haystack or "char[" in haystack or "char []" in haystack):
            return "char-pointer-vs-char-array"
        if "\\0" in haystack or "null terminator" in haystack or "终止符" in haystack:
            return "missing-null-terminator"
        if any(token in haystack for token in ("malloc(strlen", "malloc(len)", "少算一个字节", "strcpy", "memcpy")):
            return "string-allocation-off-by-one"
        if any(token in haystack for token in ("return local", "dangling", "悬空指针", "lifetime", "free(")):
            return "dangling-pointer-lifetime"
        if any(token in haystack for token in ("padding", "alignment", "对齐", "结构体")):
            return "struct-layout-alignment"
        if any(token in haystack for token in ("pointer arithmetic", "尾后一位", "越界", "arr +", "p + len")):
            return "pointer-arithmetic-off-by-one"
        if "array" in haystack and "pointer" in haystack:
            return "array-pointer-decay"
        return slugify((prompt.strip().splitlines() or ["c language error"])[0]) or "c-language-error"

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
            ("malloc", "memory-allocation"),
            ("free(", "use-after-free"),
            ("memcpy", "memcpy"),
            ("strcpy", "strcpy"),
        ]
        for needle, label in pairs:
            if needle in haystack and label not in concepts:
                concepts.append(label)
        if "字符串" in haystack and "null-terminator" not in concepts:
            concepts.append("null-terminator")
        return self._merge_concepts([], concepts, self._infer_signature(prompt, code, analysis), None)

    def _canonicalize_signature(self, raw_signature: str, payload: ErrorCaptureRequest) -> str:
        label = slugify(raw_signature)
        if label in KNOWN_SIGNATURES:
            return label
        haystack = f"{label}\n{payload.prompt}\n{payload.code}\n{payload.user_analysis}".lower()
        if ("function" in haystack and "parameter" in haystack) or "形参" in haystack:
            return "function-parameter-decay"
        mentions_string_length = any(
            token in haystack for token in ("strlen", "string length", "字符串长度", "逻辑长度", "可见长度")
        ) or ("长度" in haystack and any(token in haystack for token in ("char", "字符串", '"')))
        if "sizeof" in haystack and '"' in haystack and ("char" in haystack or "字符串" in haystack):
            return "sizeof-vs-strlen"
        if "sizeof" in haystack and mentions_string_length:
            return "sizeof-vs-strlen"
        if "&arr" in haystack or ("address" in haystack and "array" in haystack):
            return "arr-vs-address-of-array"
        if "char-pointer" in label or ("char" in haystack and "pointer" in haystack and "array" in haystack):
            return "char-pointer-vs-char-array"
        if "null" in haystack or "\\0" in haystack:
            return "missing-null-terminator"
        if "malloc" in haystack or "strcpy" in haystack or "memcpy" in haystack:
            return "string-allocation-off-by-one"
        if "dangling" in haystack or "free" in haystack or "lifetime" in haystack:
            return "dangling-pointer-lifetime"
        if "struct" in haystack or "alignment" in haystack or "padding" in haystack:
            return "struct-layout-alignment"
        if "pointer-arithmetic" in label or "尾后一位" in haystack or "越界" in haystack:
            return "pointer-arithmetic-off-by-one"
        if "array" in haystack and "pointer" in haystack:
            return "array-pointer-decay"
        return self._infer_signature(payload.prompt, payload.code, payload.user_analysis)

    def _normalize_title(self, title: str) -> str:
        cleaned = re.sub(r"\s+", " ", title).strip(" -:：")
        cleaned = cleaned.replace("versus", "vs").replace("VS", "vs")
        return cleaned or "C 语言错题"

    def _clean_sentence(self, value: str, fallback: str) -> str:
        cleaned = re.sub(r"\s+", " ", value).strip()
        if not cleaned:
            return fallback
        if cleaned.lower().startswith(("the learner", "this submission", "the note")):
            return fallback
        return cleaned

    def _merge_concepts(
        self,
        model_concepts: list[str],
        fallback_concepts: list[str],
        signature: str,
        payload: ErrorCaptureRequest | None,
    ) -> list[str]:
        extracted = [*REQUIRED_CONCEPTS.get(signature, [])]
        optional_allowed = OPTIONAL_CONCEPTS.get(signature)
        if signature in KNOWN_SIGNATURES:
            for concept in fallback_concepts:
                canonical = self._canonicalize_concept(concept)
                if canonical in extracted:
                    continue
                if optional_allowed is not None and canonical not in optional_allowed:
                    continue
                extracted.append(canonical)
        else:
            extracted.extend(fallback_concepts)
        if signature not in KNOWN_SIGNATURES:
            extracted.extend(model_concepts)
        if payload is not None:
            haystack = f"{payload.prompt}\n{payload.code}\n{payload.user_analysis}".lower()
            if "&arr" in haystack and "address-of-array" not in extracted:
                extracted.append("address-of-array")
            if "arr" in haystack and "array" not in extracted and self._allows_optional(signature, "array"):
                extracted.append("array")
            if "pointer" in haystack and "pointer" not in extracted and self._allows_optional(signature, "pointer"):
                extracted.append("pointer")
            if "char *" in haystack and "char-pointer" not in extracted and self._allows_optional(signature, "char-pointer"):
                extracted.append("char-pointer")
            if (
                '="' not in haystack
                and '"' in haystack
                and "string-literal" not in extracted
                and self._allows_optional(signature, "string-literal")
            ):
                extracted.append("string-literal")
        return self._normalize_concepts(extracted)

    def _allows_optional(self, signature: str, concept: str) -> bool:
        if signature not in KNOWN_SIGNATURES:
            return True
        return concept in OPTIONAL_CONCEPTS.get(signature, set())

    def _normalize_concepts(self, concepts: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in concepts:
            key = self._canonicalize_concept(item)
            if not key or key in seen or self._is_bad_concept_label(key):
                continue
            seen.add(key)
            normalized.append(key)
        return normalized[:5] or ["pointer-semantics"]

    def _canonicalize_concept(self, concept: str) -> str:
        text = concept.strip().lower()
        if not text:
            return ""
        raw_slug = slugify(text).strip("-")
        combo_tokens = {token for token in raw_slug.split("-") if token}
        if len(combo_tokens) >= 2 and combo_tokens <= {"strlen", "strcpy", "malloc", "memory", "allocation"}:
            return "memory-allocation"
        text = text.replace("&", " and ")
        text = re.sub(r"[_/]+", "-", text)
        text = re.sub(r"\s+", " ", text)
        if text in CONCEPT_ALIASES:
            return CONCEPT_ALIASES[text]
        slug = slugify(text).strip("-")
        return CONCEPT_ALIASES.get(slug, slug)

    def _normalize_tags(self, tags: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in tags:
            label = slugify(item).strip("-")
            if not label or label in seen or self._is_bad_concept_label(label):
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

    def _is_bad_concept_label(self, label: str) -> bool:
        if not label or label.isdigit():
            return True
        return label in BAD_CONCEPTS

    def _build_evidence(self, payload: ErrorCaptureRequest) -> list[str]:
        evidence: list[str] = []
        prompt_line = payload.prompt.strip().splitlines()[0].strip() if payload.prompt.strip() else ""
        if prompt_line:
            evidence.append(f"题面/描述：{prompt_line[:120]}")
        analysis_line = payload.user_analysis.strip().splitlines()[0].strip() if payload.user_analysis.strip() else ""
        if analysis_line:
            evidence.append(f"自我分析：{analysis_line[:120]}")
        code_line = payload.code.strip().splitlines()[0].strip() if payload.code.strip() else ""
        if code_line:
            evidence.append(f"代码线索：{code_line[:120]}")
        return evidence[:3] or ["题面和自我分析已经暴露出这次误判的直接线索。"]

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
