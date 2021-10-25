```python
from returns.result import Result, Success, Failure

def find_user(user_id: int) -> Result['User', str]:
    user = User.objects.filter(id=user_id)
    if user.exists():
        return Success(user[0])
    return Failure('User was not found')

user_search_result = find_user(1)
# => Success(User{id: 1, ...})

user_search_result = find_user(0)  # id 0 does not exist!
# => Failure('User was not found')
```

```python
from enact.exc import throw, try_eval, ReturnWithFx


def find_user(user_id: int) -> ReturnWithFx[ValueError, 'User']:
    user = User.objects.filter(id=user_id)
    if user.exists():
        return user[0]
    yield from throw(ValueError('User was not found'))


user_search_result = try_eval(find_user(1))
# => User{id: 1, ...}

user_search_result = try_eval(find_user(0))  # id 0 does not exist!
# => ValueError('User was not found')
```

---

```python
from returns.result import Result, Success, Failure
from returns.pointfree import bind
from returns.pipeline import flow

def regular_function(arg: int) -> float:
    return float(arg)

def returns_container(arg: float) -> Result[str, ValueError]:
    if arg != 0:
        return Success(str(arg))
    return Failure(ValueError('Wrong arg'))

def also_returns_container(arg: str) -> Result[str, ValueError]:
    return Success(arg + '!')

assert flow(
    1,  # initial value
    regular_function,  # composes easily
    returns_container,  # also composes easily, but returns a container
    # So we need to `bind` the next function to allow it to consume
    # the container from the previous step.
    bind(also_returns_container),
) == Success('1.0!')

# And this will fail:
assert flow(
    0,  # initial value
    regular_function,  # composes easily
    returns_container,  # also composes easily, but returns a container
    # So we need to `bind` the next function to allow it to consume
    # the container from the previous step.
    bind(also_returns_container),
).failure().args == ('Wrong arg', )
```

```python
from enact.exc import throw, try_eval, ReturnWithFx


def regular_function(arg: int) -> float:
    return float(arg)


def returns_container(arg: float) -> ReturnWithFx[ValueError, str]:
    if arg != 0:
        return str(arg)
    yield from throw(ValueError('Wrong arg'))


def also_returns_container(arg: str) -> str:
    return arg + '!'


def flow(x: int) -> ReturnWithFx[ValueError, str]:
    y = yield from returns_container(regular_function)
    return also_returns_container(y)


try_eval(flow(1))
try_eval(flow(0))
```
