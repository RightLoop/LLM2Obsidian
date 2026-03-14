"""Write smart nodes into the vault and local metadata store."""

from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy.orm import sessionmaker

from obsidian_agent.domain.enums import (
    KnowledgeNodeType,
    KnowledgeRelationType,
    NoteKind,
    NoteStatus,
    SourceType,
)
from obsidian_agent.domain.schemas import (
    ActionPreview,
    ErrorCaptureRequest,
    ErrorObject,
    FrontmatterSchema,
    KnowledgeEdgeSchema,
    KnowledgeNodeSchema,
    WeaknessObject,
)
from obsidian_agent.services.obsidian_service import ObsidianService
from obsidian_agent.storage.repositories import (
    ErrorOccurrenceRepository,
    KnowledgeEdgeRepository,
    KnowledgeNodeRepository,
)
from obsidian_agent.utils.markdown import render_template
from obsidian_agent.utils.slugify import slugify
from obsidian_agent.utils.time import compact_timestamp, now_utc


class NodeWriterService:
    """Persist smart nodes, reuse near-duplicates, and link them together."""

    def __init__(
        self,
        session_factory: sessionmaker,
        obsidian_service: ObsidianService,
        error_template_path: Path,
        smart_node_template_path: Path,
    ) -> None:
        self.session_factory = session_factory
        self.obsidian_service = obsidian_service
        self.error_template_path = error_template_path
        self.smart_node_template_path = smart_node_template_path

    async def write_error_bundle(
        self,
        request: ErrorCaptureRequest,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
    ) -> tuple[KnowledgeNodeSchema, list[KnowledgeNodeSchema], ActionPreview | None, int]:
        action_previews: list[ActionPreview] = []
        error_node = await self._write_or_reuse_error_node(
            request,
            error,
            weaknesses,
            action_previews,
        )
        supporting_nodes = await self._write_or_reuse_supporting_nodes(
            error=error,
            weaknesses=weaknesses,
            source_note_path=error_node.note_path,
            action_previews=action_previews,
        )

        with self.session_factory() as session:
            node_repo = KnowledgeNodeRepository(session)
            error_entity = node_repo.get_by_key(error_node.node_key)
            if error_entity is None:
                raise ValueError(f"Stored error node not found: {error_node.node_key}")
            ErrorOccurrenceRepository(session).create(
                error=error,
                raw_input=self._compose_raw_input(request),
                node_id=error_entity.id,
                source_note_path=error_node.note_path,
            )
            stored_edges = KnowledgeEdgeRepository(session).create_if_missing_batch(
                from_node_id=error_entity.id,
                edges=self._build_supporting_edges(error, error_node.node_key, supporting_nodes),
                node_ids_by_key={
                    entity.node_key: entity.id
                    for entity in node_repo.list_all()
                    if entity.id is not None
                },
            )

        preview = None
        if action_previews:
            preview = ActionPreview(
                dry_run=True,
                action="write_error_bundle",
                target_path=error_node.note_path or "",
                details={
                    "generated_paths": [item.target_path for item in action_previews],
                    "generated_count": len(action_previews),
                },
            )
        return error_node, supporting_nodes, preview, len(stored_edges)

    async def _write_or_reuse_error_node(
        self,
        request: ErrorCaptureRequest,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
        action_previews: list[ActionPreview],
    ) -> KnowledgeNodeSchema:
        node_key = f"error/{slugify(error.error_signature)}"
        existing = self._load_existing_node(node_key)
        note_path = existing.note_path if existing else None
        if not note_path:
            frontmatter = FrontmatterSchema(
                id=compact_timestamp(),
                kind=NoteKind.ERROR,
                status=NoteStatus.DRAFT,
                source_type=SourceType.MANUAL,
                source_ref=request.source_ref,
                created_at=now_utc(),
                updated_at=now_utc(),
                tags=error.tags,
                entities=[],
                topics=error.related_concepts,
                confidence=error.confidence,
                review_required=False,
            )
            body = render_template(
                self.error_template_path,
                {
                    "title": error.title,
                    "summary": error.summary,
                    "trigger_mistake": error.trigger_mistake,
                    "root_cause": error.root_cause,
                    "incorrect_assumption": error.incorrect_assumption,
                    "corrective_rule": error.corrective_rule,
                    "next_time_checklist": "\n".join(
                        f"- {item}" for item in error.next_time_checklist
                    )
                    or "-",
                    "evidence": "\n".join(f"- {item}" for item in error.evidence) or "-",
                    "related_concepts": "\n".join(
                        f"- {self._concept_label(item)}" for item in error.related_concepts
                    )
                    or "-",
                    "recommended_practice": "\n".join(
                        f"- {item.recommended_practice}" for item in weaknesses
                    )
                    or "-",
                },
            )
            write_result = await self.obsidian_service.create_note(
                folder=self.obsidian_service.settings.smart_errors_folder,
                title=error.title,
                frontmatter=frontmatter.model_dump(mode="json"),
                body=body,
            )
            if hasattr(write_result, "model_dump"):
                note_path = write_result.target_path
                action_previews.append(write_result)
            else:
                note_path = write_result

        node = KnowledgeNodeSchema(
            id=existing.id if existing else None,
            node_key=node_key,
            node_type=KnowledgeNodeType.ERROR,
            title=existing.title if existing else error.title,
            summary=existing.summary if existing and len(existing.summary) >= len(error.summary) else error.summary,
            note_path=note_path,
            source_note_path=request.source_ref or None,
            tags=sorted({*(existing.tags if existing else []), *error.tags}),
            metadata={
                "language": error.language,
                "error_signature": error.error_signature,
                "trigger_mistake": error.trigger_mistake,
                "root_cause": error.root_cause,
                "incorrect_assumption": error.incorrect_assumption,
                "corrective_rule": error.corrective_rule,
                "next_time_checklist": error.next_time_checklist,
                "weaknesses": [item.model_dump(mode="json") for item in weaknesses],
            },
        )
        with self.session_factory() as session:
            stored = KnowledgeNodeRepository(session).upsert(node)
        return self._entity_to_schema(stored)

    async def _write_or_reuse_supporting_nodes(
        self,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
        source_note_path: str | None,
        action_previews: list[ActionPreview],
    ) -> list[KnowledgeNodeSchema]:
        specs = self._build_supporting_specs(error, weaknesses, source_note_path)
        stored_nodes: list[KnowledgeNodeSchema] = []
        for spec in specs:
            reused = self._find_existing_support_node(spec)
            note_path = reused.note_path if reused else None
            merged_tags = sorted({*(reused.tags if reused else []), *spec.tags})
            merged_metadata = dict(reused.metadata if reused else {})
            merged_metadata.update(spec.metadata)
            summary = self._preferred_support_summary(reused.summary, spec.summary) if reused else spec.summary
            title = self._preferred_support_title(reused.title, spec.title, spec.node_type) if reused else spec.title
            node_key = reused.node_key if reused else spec.node_key

            if not note_path:
                frontmatter = FrontmatterSchema(
                    id=compact_timestamp(),
                    kind=self._note_kind_for_node(spec.node_type),
                    status=NoteStatus.DRAFT,
                    source_type=SourceType.MANUAL,
                    source_ref=source_note_path or "",
                    created_at=now_utc(),
                    updated_at=now_utc(),
                    tags=merged_tags,
                    entities=[],
                    topics=[str(item) for item in merged_metadata.get("related_concepts", [])],
                    confidence=0.6,
                    review_required=False,
                )
                body = render_template(
                    self.smart_node_template_path,
                    {
                        "title": title,
                        "summary": summary,
                        "node_type": self._node_type_label(spec.node_type),
                        "durable_rule": str(merged_metadata.get("durable_rule", "-")),
                        "key_distinction": str(merged_metadata.get("key_distinction", "-")),
                        "when_to_use": str(merged_metadata.get("when_to_use", "-")),
                        "avoid_confusion": str(merged_metadata.get("avoid_confusion", "-")),
                        "related_concepts": "\n".join(
                            f"- {self._concept_label(item)}"
                            for item in merged_metadata.get("related_concepts", [])
                        )
                        or "-",
                        "evidence": "\n".join(
                            f"- {item}" for item in merged_metadata.get("evidence", [])
                        )
                        or "-",
                    },
                )
                write_result = await self.obsidian_service.create_note(
                    folder=self.obsidian_service.settings.smart_nodes_folder,
                    title=title,
                    frontmatter=frontmatter.model_dump(mode="json"),
                    body=body,
                )
                if hasattr(write_result, "model_dump"):
                    note_path = write_result.target_path
                    action_previews.append(write_result)
                else:
                    note_path = write_result

            node = KnowledgeNodeSchema(
                id=reused.id if reused else None,
                node_key=node_key,
                node_type=spec.node_type,
                title=title,
                summary=summary,
                note_path=note_path,
                source_note_path=source_note_path,
                tags=merged_tags,
                metadata=merged_metadata,
            )
            with self.session_factory() as session:
                stored = KnowledgeNodeRepository(session).upsert(node)
            stored_nodes.append(self._entity_to_schema(stored))
        return stored_nodes

    def _build_supporting_specs(
        self,
        error: ErrorObject,
        weaknesses: list[WeaknessObject],
        source_note_path: str | None,
    ) -> list[KnowledgeNodeSchema]:
        nodes: list[KnowledgeNodeSchema] = []
        concept_seen: set[str] = set()
        for weakness in weaknesses:
            for concept in weakness.related_concepts[:2]:
                node_key = f"concept/{slugify(concept)}"
                if node_key in concept_seen:
                    continue
                concept_seen.add(node_key)
                title = self._concept_title(concept)
                nodes.append(
                    KnowledgeNodeSchema(
                        node_key=node_key,
                        node_type=KnowledgeNodeType.CONCEPT,
                        title=title,
                        summary=self._concept_summary(concept, error),
                        note_path=None,
                        source_note_path=source_note_path,
                        tags=["concept", error.language, *error.tags[:2]],
                        metadata={
                            "durable_rule": self._concept_rule(concept, error),
                            "key_distinction": self._concept_distinction(concept, error),
                            "when_to_use": self._concept_usage(concept, error),
                            "avoid_confusion": error.incorrect_assumption,
                            "related_concepts": weakness.related_concepts,
                            "derived_from_error": error.error_signature,
                            "evidence": error.evidence[:2],
                        },
                    )
                )

        nodes.append(
            KnowledgeNodeSchema(
                node_key=f"pitfall/{slugify(error.error_signature)}",
                node_type=KnowledgeNodeType.PITFALL,
                title=f"易错点：{error.title}",
                summary=f"这类错误通常发生在：{error.trigger_mistake}",
                note_path=None,
                source_note_path=source_note_path,
                tags=["pitfall", error.language, *error.tags[:2]],
                metadata={
                    "durable_rule": error.corrective_rule,
                    "key_distinction": error.root_cause,
                    "when_to_use": "做题时遇到相似表达式、内存布局或边界判断题时，先按规则逐项核对。",
                    "avoid_confusion": error.incorrect_assumption,
                    "related_concepts": error.related_concepts,
                    "derived_from_error": error.error_signature,
                    "evidence": error.evidence,
                },
            )
        )

        contrast_title = self._contrast_title(error)
        if contrast_title:
            nodes.append(
                KnowledgeNodeSchema(
                    node_key=f"contrast/{slugify(contrast_title)}",
                    node_type=KnowledgeNodeType.CONTRAST,
                    title=contrast_title,
                    summary=self._contrast_summary(error),
                    note_path=None,
                    source_note_path=source_note_path,
                    tags=["contrast", error.language, *error.tags[:2]],
                    metadata={
                        "durable_rule": self._contrast_rule(error),
                        "key_distinction": error.root_cause,
                        "when_to_use": "当题目同时出现这两个相邻概念，或你准备直接套结论时，先停下来做对比。",
                        "avoid_confusion": error.incorrect_assumption,
                        "related_concepts": error.related_concepts,
                        "derived_from_error": error.error_signature,
                        "evidence": error.evidence,
                    },
                )
            )
        return nodes

    def _find_existing_support_node(self, candidate: KnowledgeNodeSchema) -> KnowledgeNodeSchema | None:
        direct = self._load_existing_node(candidate.node_key)
        if direct is not None:
            return direct
        normalized_title = self._normalize_text(candidate.title)
        with self.session_factory() as session:
            repo = KnowledgeNodeRepository(session)
            for entity in repo.list_all():
                if entity.node_type != candidate.node_type.value:
                    continue
                existing = self._entity_to_schema(entity)
                if self._normalize_text(existing.title) == normalized_title:
                    return existing
        return None

    def _build_supporting_edges(
        self,
        error: ErrorObject,
        error_node_key: str,
        nodes: list[KnowledgeNodeSchema],
    ) -> list[KnowledgeEdgeSchema]:
        edges: list[KnowledgeEdgeSchema] = []
        for node in nodes:
            relation_type = KnowledgeRelationType.COMMONLY_CONFUSED_WITH
            reason = "这条链接指向本次错题里最容易混淆的相邻概念。"
            if node.node_type == KnowledgeNodeType.CONCEPT:
                relation_type = KnowledgeRelationType.REVEALS_GAP_IN
                reason = f"这次错题直接暴露出对“{node.title}”的理解缺口。"
            elif node.node_type == KnowledgeNodeType.CONTRAST:
                relation_type = KnowledgeRelationType.CONTRASTS_WITH
                label = node.title.replace("对比：", "").replace("对比:", "").strip()
                reason = f"这次题目需要把“{label}”明确区分开。"
            edges.append(
                KnowledgeEdgeSchema(
                    from_node_key=error_node_key,
                    to_node_key=node.node_key,
                    relation_type=relation_type,
                    reason=reason,
                    confidence=max(0.55, error.confidence),
                )
            )
        return edges

    def _load_existing_node(self, node_key: str) -> KnowledgeNodeSchema | None:
        with self.session_factory() as session:
            entity = KnowledgeNodeRepository(session).get_by_key(node_key)
        return self._entity_to_schema(entity) if entity is not None else None

    def _entity_to_schema(self, entity) -> KnowledgeNodeSchema:
        return KnowledgeNodeSchema(
            id=entity.id,
            node_key=entity.node_key,
            node_type=KnowledgeNodeType(entity.node_type),
            title=entity.title,
            summary=entity.summary,
            note_path=entity.note_path,
            source_note_path=entity.source_note_path,
            tags=json.loads(entity.tags_json or "[]"),
            metadata=json.loads(entity.metadata_json or "{}"),
        )

    def _compose_raw_input(self, request: ErrorCaptureRequest) -> str:
        return (
            f"Prompt:\n{request.prompt}\n\n"
            f"Code:\n{request.code}\n\n"
            f"Analysis:\n{request.user_analysis}\n"
        ).strip()

    def _contrast_title(self, error: ErrorObject) -> str | None:
        signature = error.error_signature.lower()
        if "-vs-" in signature:
            left, right = signature.split("-vs-", maxsplit=1)
            return f"对比：{self._concept_title(left)} vs {self._concept_title(right)}"
        if signature not in {
            "sizeof-vs-strlen",
            "arr-vs-address-of-array",
            "char-pointer-vs-char-array",
        }:
            return None
        concepts = error.related_concepts[:2]
        if len(concepts) >= 2:
            return f"对比：{self._concept_title(concepts[0])} vs {self._concept_title(concepts[1])}"
        if "arr" in error.incorrect_assumption.lower() and "&arr" in " ".join(error.evidence).lower():
            return "对比：arr vs &arr"
        return None

    def _concept_title(self, concept: str) -> str:
        mapping = {
            "sizeof": "sizeof 的语义",
            "strlen": "strlen 的语义",
            "pointer": "指针语义",
            "array": "数组对象",
            "array-decay": "数组退化",
            "char-pointer": "char* 指针",
            "char-array": "char[] 数组",
            "string-literal": "字符串字面量",
            "function-parameter": "函数形参与退化",
            "address-of-array": "整个数组对象的地址",
            "null-terminator": "字符串结尾空字符",
            "memory-allocation": "内存分配容量",
            "memory-alignment": "内存对齐",
            "struct-padding": "结构体填充",
            "pointer-lifetime": "指针生命周期",
            "pointer-arithmetic": "指针偏移边界",
            "array-boundary": "数组边界",
            "buffer-capacity": "缓冲区容量",
            "dangling-pointer": "悬空指针",
            "stack-memory": "栈上对象生命周期",
            "heap-memory": "堆内存生命周期",
            "use-after-free": "释放后继续使用",
            "dynamic-array": "动态数组容量",
            "multi-dimensional-array": "多维数组退化",
            "pointer-level": "指针层级",
            "struct-layout": "结构体布局",
            "cstring": "C 字符串约束",
            "memcpy": "memcpy 拷贝边界",
        }
        return mapping.get(concept, concept.replace("-", " "))

    def _concept_label(self, concept: str) -> str:
        return self._concept_title(concept)

    def _concept_summary(self, concept: str, error: ErrorObject) -> str:
        mapping = {
            "sizeof": "sizeof 计算的是表达式或类型在当前语境下占用的字节数，不负责回答字符串逻辑长度。",
            "strlen": "strlen 从起始地址向后扫描，直到遇到 \\0，返回的是字符串逻辑长度而不是占用总字节数。",
            "pointer": "指针变量保存的是地址值，本身有自己的大小、类型和可解引用边界。",
            "array": "数组对象是一段连续存储空间，元素个数属于对象本体信息，不等于普通指针变量。",
            "array-decay": "数组在大多数表达式里会退化成首元素指针，但并不是所有语境都发生退化。",
            "char-pointer": "char* 表示一个保存字符地址的指针变量，不代表它拥有对应字符存储。",
            "char-array": "char[] 是真正存放字符的数组对象，容量和内容都属于对象本体。",
            "string-literal": "字符串字面量通常位于只读存储区域，不能因为被 char* 指向就默认可写。",
            "function-parameter": "数组作为函数形参时会按指针语义处理，调用点的数组长度不会自动保留。",
            "address-of-array": "&arr 指向整个数组对象，类型层级与 arr 退化后的首元素指针不同。",
            "null-terminator": "合法的 C 字符串必须以 \\0 结尾；终止符既影响遍历，也影响容量判断。",
            "memory-allocation": "字符串相关内存分配必须同时考虑可见字符、终止符和目标缓冲区容量。",
            "memory-alignment": "内存对齐要求会改变对象在内存中的起始位置和整体大小。",
            "struct-padding": "结构体为了满足成员和整体对齐，可能插入 padding 字节。",
            "pointer-lifetime": "地址值存在不代表对象仍然有效，指针是否可用取决于被指对象的生命周期。",
            "pointer-arithmetic": "指针偏移的结果必须同时满足类型正确和边界合法，尾后一位不能解引用。",
            "array-boundary": "数组最后一个有效元素和尾后一位是两个不同的边界概念。",
            "buffer-capacity": "缓冲区容量讨论的是最多能安全写入多少字节，不等于当前已有内容长度。",
        }
        return mapping.get(concept, f"这个概念是理解“{error.title}”时必须先分清的判断边界。")

    def _concept_rule(self, concept: str, error: ErrorObject) -> str:
        mapping = {
            "sizeof": "先确认自己在求“占用字节数”还是“逻辑长度”；只有前者才优先考虑 sizeof。",
            "strlen": "只有在确定内存里存在合法 C 字符串时，才能用 strlen 讨论其逻辑长度。",
            "pointer": "先写出指针指向的对象类型，再判断它是否还能被安全解引用。",
            "array": "看到数组时先把它当“对象”理解，而不是先把它当普通指针变量。",
            "array-decay": "每次看到数组参与表达式，都先问一句：这里有没有发生退化？",
            "char-pointer": "char* 默认只说明“保存了字符地址”，不说明那段字符一定可写。",
            "char-array": "char[] 默认说明“对象自己拥有存储空间”，容量必须单独核对。",
            "string-literal": "看到字符串字面量时，先把它当作只读字符序列，而不是可随意原地修改的数组。",
            "function-parameter": "数组进入函数后按指针处理，需要长度就显式传入，不靠 sizeof 猜。",
            "address-of-array": "看到 &arr 时先写类型，再判断它是“整个数组对象地址”，不是首元素地址。",
            "null-terminator": "只要题目涉及 C 字符串，就把 \\0 当成真实占位字节一起考虑。",
            "memory-allocation": "做容量分配时始终把“可见字符 + 终止符 + 目标缓冲区约束”一起算。",
            "memory-alignment": "估算内存大小前，先列出每个对象的对齐要求。",
            "struct-padding": "算结构体大小时不要直接相加成员 sizeof，先按布局顺序推 padding。",
            "pointer-lifetime": "保留地址之前先确认对象在后续使用点前不会结束生命周期。",
            "pointer-arithmetic": "偏移后先判断它是不是仍处在合法可解引用区间，再使用结果。",
            "array-boundary": "遇到索引和偏移时，先把最后一个有效位置和尾后一位分开标出来。",
        }
        return mapping.get(concept, error.corrective_rule)

    def _concept_distinction(self, concept: str, error: ErrorObject) -> str:
        mapping = {
            "sizeof": "要和 strlen、对象容量、元素个数这些概念区分开。",
            "strlen": "要和 sizeof、缓冲区容量、已分配字节数区分开。",
            "pointer": "要和数组对象、被指对象本体、尾后一位位置区分开。",
            "array": "要和数组退化后的指针值、可变指针变量区分开。",
            "array-decay": "要和“数组对象本体仍然存在”这件事区分开。",
            "char-pointer": "要和 char[] 数组、字符串字面量可写性区分开。",
            "char-array": "要和 char* 指针变量、字面量地址区分开。",
            "string-literal": "要和可写数组对象、动态分配缓冲区区分开。",
            "function-parameter": "要和调用点处真实数组对象及其长度信息区分开。",
            "address-of-array": "要和首元素地址、一级指针类型区分开。",
            "null-terminator": "要和可见字符、缓冲区容量、拷贝字节数区分开。",
            "memory-allocation": "要和逻辑长度、对象大小、当前已写内容区分开。",
            "memory-alignment": "要和成员表面大小直接相加的直觉区分开。",
            "struct-padding": "要和“成员之间没有空洞”的假设区分开。",
            "pointer-lifetime": "要和“地址值还在”这种表面现象区分开。",
            "pointer-arithmetic": "要和普通整数加减、数组索引直觉区分开。",
            "array-boundary": "要和尾后一位、可比较位置、可解引用位置区分开。",
        }
        return mapping.get(concept, error.root_cause)

    def _concept_usage(self, concept: str, error: ErrorObject) -> str:
        mapping = {
            "sizeof": "判断对象大小、类型大小、静态数组总字节数时使用。",
            "strlen": "确认合法 C 字符串逻辑长度时使用。",
            "pointer": "推理间接访问、动态内存、函数参数和边界移动时使用。",
            "array": "推理对象容量、元素布局和不会被重新赋值的数组本体时使用。",
            "array-decay": "判断数组进表达式、函数参数和指针运算时是否按指针语义处理时使用。",
            "char-pointer": "判断地址来源、可写性和是否拥有存储空间时使用。",
            "char-array": "判断容量、终止符空间和原地修改时使用。",
            "string-literal": "判断字符序列是否可写、是否位于只读区以及能否原地修改时使用。",
            "function-parameter": "分析函数内部的 sizeof、长度判断和形参语义时使用。",
            "address-of-array": "分析多维数组、数组整体地址和指针类型时使用。",
            "null-terminator": "分析字符串拷贝、拼接、遍历和容量分配时使用。",
            "memory-allocation": "分析 malloc、calloc、缓冲区大小和字符串拷贝前的容量判断时使用。",
            "memory-alignment": "分析 ABI、结构体大小和性能布局时使用。",
            "struct-padding": "分析结构体 sizeof、二进制布局和字段顺序影响时使用。",
            "pointer-lifetime": "分析返回地址、free 之后访问和悬空引用时使用。",
            "pointer-arithmetic": "分析 p + n、尾后一位和偏移后解引用是否合法时使用。",
            "array-boundary": "分析数组末尾、循环边界和偏移落点是否合法时使用。",
        }
        return mapping.get(concept, f"在处理“{error.title}”这一类题目时使用。")

    def _contrast_summary(self, error: ErrorObject) -> str:
        return f"这组对比用于拆开“{error.title}”里最容易被混为一谈的两个概念。"

    def _contrast_rule(self, error: ErrorObject) -> str:
        return "做题时先把两边概念各自的类型、对象层级或长度定义写出来，再判断结论。"

    def _normalize_text(self, text: str) -> str:
        lowered = text.lower().strip()
        lowered = lowered.replace("&arr", "address-of-array")
        lowered = lowered.replace("char[]", "char-array")
        lowered = lowered.replace("char *", "char-pointer")
        lowered = lowered.replace("char*", "char-pointer")
        lowered = lowered.replace("&", " and ")
        lowered = re.sub(r"[^\w\u4e00-\u9fff]+", " ", lowered)
        tokens = [token for token in lowered.split() if token not in {"the", "a", "an", "in", "of"}]
        return " ".join(tokens)

    def _preferred_support_title(
        self,
        existing_title: str,
        candidate_title: str,
        node_type: KnowledgeNodeType,
    ) -> str:
        title = (existing_title or "").strip()
        if not title:
            return candidate_title
        legacy_prefixes = ("Pitfall:", "Contrast:", "Weakness:")
        if title.startswith(legacy_prefixes):
            return candidate_title
        if node_type == KnowledgeNodeType.CONCEPT and title.isascii() and len(title.split()) <= 2:
            return candidate_title
        return title

    def _preferred_support_summary(self, existing_summary: str, candidate_summary: str) -> str:
        summary = (existing_summary or "").strip()
        if not summary:
            return candidate_summary
        low_quality_markers = (
            "The learner repeatedly confuses",
            "Fallback relation inferred",
            "Related concept",
        )
        if any(marker in summary for marker in low_quality_markers):
            return candidate_summary
        return summary

    def _node_type_label(self, node_type: KnowledgeNodeType) -> str:
        mapping = {
            KnowledgeNodeType.ERROR: "错误节点",
            KnowledgeNodeType.CONCEPT: "概念节点",
            KnowledgeNodeType.CONTRAST: "对比节点",
            KnowledgeNodeType.PITFALL: "易错点节点",
        }
        return mapping[node_type]

    @staticmethod
    def _note_kind_for_node(node_type: KnowledgeNodeType) -> NoteKind:
        mapping = {
            KnowledgeNodeType.ERROR: NoteKind.ERROR,
            KnowledgeNodeType.CONCEPT: NoteKind.CONCEPT,
            KnowledgeNodeType.CONTRAST: NoteKind.CONTRAST,
            KnowledgeNodeType.PITFALL: NoteKind.PITFALL,
        }
        return mapping[node_type]
