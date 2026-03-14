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
