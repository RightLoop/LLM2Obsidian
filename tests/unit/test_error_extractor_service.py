from obsidian_agent.domain.schemas import ErrorCaptureRequest
from obsidian_agent.services.error_extractor_service import ErrorExtractorService


def test_infer_signature_detects_sizeof_vs_strlen_for_char_string_case() -> None:
    service = ErrorExtractorService.__new__(ErrorExtractorService)
    signature = service._infer_signature(
        "我以为 sizeof(arr) 得到的就是字符串 abc 的长度 3。",
        'char arr[] = "abc";\nprintf("%zu\\n", sizeof(arr));',
        "我把数组占用字节数和字符串逻辑长度看成了一回事。",
    )
    assert signature == "sizeof-vs-strlen"


def test_infer_signature_preserves_function_parameter_decay_when_printf_has_quotes() -> None:
    service = ErrorExtractorService.__new__(ErrorExtractorService)
    signature = service._infer_signature(
        "我以为函数参数写成 int arr[10] 后，sizeof(arr) 还能得到数组长度。",
        'void f(int arr[10]) {\n    printf("%zu\\n", sizeof(arr));\n}',
        "我忽略了数组作为形参时会退化成指针。",
    )
    assert signature == "function-parameter-decay"


def test_sanitize_prefers_llm_signature_when_provider_output_is_reliable() -> None:
    service = ErrorExtractorService.__new__(ErrorExtractorService)
    service.last_telemetry = {
        "provider": "deepseek",
        "response_chars": 800,
    }
    payload = ErrorCaptureRequest(
        title='char *p = "abc"; sizeof(p)',
        prompt='我看到 char *p = "abc"; 又看到了 sizeof(p)，就把它当成字符串长度题了。',
        code='char *p = "abc";\nprintf("%zu\\n", sizeof(p));',
        user_analysis="我混淆了指针大小、字符串字面量和字符数组。",
        language="c",
    )
    sanitized = service._sanitize(
        {"error_signature": "char-pointer-vs-char-array"},
        payload,
    )
    assert sanitized["error_signature"] == "char-pointer-vs-char-array"


def test_sanitize_prefers_fallback_signature_for_repaired_sparse_ollama_output() -> None:
    service = ErrorExtractorService.__new__(ErrorExtractorService)
    service.last_telemetry = {
        "provider": "ollama",
        "response_chars": 5,
        "repaired": True,
    }
    payload = ErrorCaptureRequest(
        title="函数里用 sizeof(arr) 求形参数组长度",
        prompt="我以为函数参数写成 int arr[10]，在函数里 sizeof(arr) 还能得到 10 个元素的大小。",
        code='void f(int arr[10]) {\n    printf("%zu\\n", sizeof(arr));\n}',
        user_analysis="我忽略了数组作为形参时会退化成指针。",
        language="c",
    )
    sanitized = service._sanitize(
        {"error_signature": "sizeof-vs-strlen"},
        payload,
    )
    assert sanitized["error_signature"] == "function-parameter-decay"
