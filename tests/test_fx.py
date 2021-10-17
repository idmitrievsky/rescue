from enact.fx import eval_with_handler
from example.fx import add, answer_two


def test_add() -> None:
    an_int = 3

    impure_fn = add(an_int)

    assert eval_with_handler(impure_fn, answer_two) == 5
