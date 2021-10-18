from enact.fx import eval_with_handler
from example.fx import add, answer_two


def test_add() -> None:
    impure_fn = add()

    assert eval_with_handler(impure_fn, answer_two) == 4
