from functions.relaxometry.prompt_input import prompt_input

def test_prompt_input(monkeypatch, capsys):
    answers = iter(["5", "3"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))

    result = prompt_input("Enter: ", 1, 3)

    captured = capsys.readouterr()

    assert result == 3
    assert "Error: Enter a number from range 1 to 3" in captured.out
