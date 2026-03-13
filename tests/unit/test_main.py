from src.main import main


def test_main_prints_ready_message(capsys) -> None:
    main()
    captured = capsys.readouterr()
    assert "Project scaffold is ready." in captured.out
