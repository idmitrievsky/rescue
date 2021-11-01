<p align="center">
<h3 align="center">enact</h3>
  <p align="center">
    type-safe exception support for Python
    <br />
    <br />
    <a href="https://github.com/idmitrievsky/enact#readme">docs</a>
    ·
    <a href="https://github.com/idmitrievsky/enact/issues">issues</a>
  </p>
</p>

`enact` is a Python package with a tiny API that makes exceptions type-safe with minimal boilerplate:
- make exceptions an explicit part of function contract
- never forget to handle an exception
- build type-safe error handling abstractions

> It is also possible to use `enact` for type-safe dependency injection, but the API for that is not stable yet.

## Installation
```bash
poetry add enact
```

## Usage

| Function | Description |
| --- | --- |
| [`ReturnWithFx`](#ReturnWithFx) | Generic type to annotate error types if a function can throw. |
| [`throw`](#throw) | Halts function execution and returns an exception. |
| [`try_eval`](#try_eval) | Runs an expression when a component is initialized. |

### API

---

### `ReturnWithFx`

**Example:** `ReturnWithFx[ValueError, int]`

**Signature:** `ReturnWithFx[ExceptionType, ReturnType]`

If a function can throw an exception during its execution then we say that it returns with effects. The return value of such function has type `ReturnWithFx` with error type specified.

Think of it like the `Result` type from Rust or `Either` from Haskell, but you don't have to wrap/unwrap anything.

> Invoking a function that returns with effects doesn't start execution, but returns a generator object. To actually call the function you should delegate to it via `yield from` or evaluate it with `try_eval` or `eval_with_exc_handler`.

---

### `throw`

**Example:**
```python
def echo_even(x: int) -> ReturnWithFx[ValueError, int]:
    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))
    return x
```

**Signature:** `(exception: ExceptionType) -> ReturnWithFx[ExceptionType, NoReturn]`

`throw` halts function execution and returns an exception. It is supposed to be called via `yield from` as any other function that returns with effects.

Think of it like the `raise` that actually forces you to update the signature of a function.

> `mypy` should understand that no code is ever executed after `yield from throw(...)`, but it currently doesn't.

---

### `try_eval`
**Example:**
```python
def echo_even_or_zero(x: int) -> int:
    match try_eval(echo_even(x)):
    
    if isinstance(value, ValueError):
        return 0
        
   return value
```

**Signature:** `(ReturnWithFx[ExceptionType, ReturnType]) -> Union[ExceptionType, ReturnType]`

`try_eval` takes a `ReturnWithFx` object and evaluates it until it either returns successfully or throws an exception. `mypy` will force you to match on the result type, so can't forget to handle a potential error case.
