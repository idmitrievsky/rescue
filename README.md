<p align="center">
<h3 align="center">rescue</h3>
  <p align="center">
    type-safe exception support for Python
    <br />
    <br />
    <a href="https://github.com/idmitrievsky/rescue#readme">docs</a>
    ·
    <a href="https://github.com/idmitrievsky/rescue/issues">issues</a>
  </p>
</p>

`rescue` is a Python package that makes exceptions type-safe with minimal boilerplate

- make exceptions an explicit part of the function contract
- never forget to handle an exception
- build type-safe error handling abstractions

---

```python 
from rescue import bind, unwrap, wrap_into_exc_handler
import requests

def safe_get(
  url: str
) -> Generator[requests.HTTPError, None, Dict[str, Any]]:
  resp = requests.get(url)
  try:
      resp.raise_for_status()
  except requests.HTTPError as e:
      yield from throw(e)
  return resp.json()
  
@wrap_into_exc_handler(requests.HTTPError)
def return_empty_on_err(_: requests.HTTPError) -> Dict[str, Any]:
  return {}

data = unwrap(bind(safe_get("https://example.com"), return_empty_on_err))
```

---

- [Installation](#Installation)
- [Introduction](#Introduction)
- [API](#API)
- [Caveats](#Caveats)
- [Rationale](#Rationale)
- [Further reading](#Further-reading)

## Installation

```bash
poetry add rescue
```

Enable the plugin in `pyproject.toml`:

```toml
[tool.mypy]
disallow_untyped_defs = true
plugins = [
    "rescue.mypy",
]
```

## Introduction

Imagine that a function you write can produce an error. Let's say that this error doesn't mean that your entire program
(or thread of execution to be more precise) has to shut down, meaning the error can be handled in some way.
You just have to remember to handle this particular error every time you call the function, just in case. Sounds easy enough, right?

Turns out, it's **not easy**. People (no matter the skill level) tend to forget about stuff like this
and their programs crash unexpectedly.
I am not writing software that people rely on for their life, but even an unresponsive web page can be a nuisance.

Fear not! A lot of smart people came up with all sorts of clever tooling to help people deal with errors explicitly in cases that call for it.
This is my attempt at bringing some of these ideas to Python and mypy.

Let's say I've written a function:
```python
def echo_even(user_input: int) -> int:
  if user_input % 2 != 0:
    raise ValueError("user_input must be an even number")
  return user_input
```

With this particular implementation if I forget to add an `except` clause when calling `echo_even`, my program
will crash every time a user supplies an odd number. How do I make it impossible to call a function without explicitly handling every error it can produce?
Thankfully, I can just use `rescue`.

### `throw` instead of `raise`

Let's use `rescue.throw` to rewrite `echo_even`:

```python
from typing import Generator
from rescue import throw


def echo_even(x: int) -> Generator[ValueError, None, int]:
  if x % 2 != 0:
    yield from throw(ValueError("x must be an even number"))
  return x
```

There is a lot to unpack here. Let's begin with [Generator](#Generator).

#### `Generator` type to encode error type information
Generator is an object that represents a function call that is ready to be evaluated, but evaluation is postponed until later.
To evaluate a generator produced by `rescue` you [unwrap](#unwrap) it. As you can see from the example `Generator` is a generic type with three parameters, but `rescue` uses only two:
- the type of every possible error that can be produced by the wrapped call
- the return type of the wrapped call

> Generators are actually have a lot of other applications,
> this explanation is only for the purposes of `rescue`.

A function that returns a generator becomes a **generator function** as opposed to a regular function.
Generator functions make information about potential errors they can produce explicit through their type signature, which [greatly simplifies reasoning about the code](#Rationale). But how does a regular function become a generator function?

#### `yield from` to produce generator functions

To make your function return a generator you use `yield from` inside of it. `yield from` takes a generator as an argument and
returns a value if everything is ok. If the generator you `yield from` produces an error via `throw` then your generator function does too, which means you have
to adjust the error type part of your function signature.

`rescue` provides a [throw](#throw) function as a replacement for `raise`. `throw` is a low-level function
that returns a generator that always produces a given error when evaluated. That's why we had to specify `ValueError` as an error type for `echo_even`.

Let's look at another example:

```python
from typing import Generator, Union
from rescue import throw


def divide_if_even(x: int, y: int) -> Generator[Union[ValueError, ZeroDivisionError], None, int]:
  if y == 0:
    yield from throw(ZeroDivisionError())

  x = yield from echo_even(x)
  return x // y
```
We pass a `ZeroDivisionError()` to `throw` and `yield from` it. We have to add `ZeroDivisionError` type
to the type signature. We also `yield from` a generator that is returned by the call to `echo_even` and we know that this call
can produce a `ValueError`, so we specify it in `Generator[Union[ValueError, ZeroDivisionError], None, int]` via `Union`.

What's great about `rescue` is that you don't actually have to trace what generator functions can produce what errors,
because if you forget that `echo_even` can produce a `ValueError`, mypy will let you know by failing to type check you code!

### `unwrap` to evaluate

We can `unwrap` a generator to evaluate it only when it has `None` as the error type argument. For example, `Generator[None, None, int]` doesn't
produce any errors and returns an `int`.

```python
from rescue import unwrap

assert unwrap(add_one(5)) == 6
```

What about `echo_even` from our first example? It returns `Generator[ValueError, None, int]`, how do we turn it into `Generator[None, None, int]` so we could `unwrap` it? 

### `exc_handler` to handle errors

You can [bind](#bind) an exception handler to any generator. A handler is a callable with a single parameter of the error type it can handle. We decorate it with a
`wrap_into_exc_handler` call with the same type as argument:

```python
from rescue import bind, unwrap, wrap_into_exc_handler


@wrap_into_exc_handler(ValueError)
def return_zero(_: ValueError) -> int:
  return 0


assert unwrap(bind(echo_even(6), return_zero)) == 6
assert unwrap(bind(echo_even(5), return_zero)) == 0
```

If the execution of an `echo_even(6)` generator produces a `ValueError` the `return_zero` is executed with the error instance and its return value
becomes the return value of `unwrap`. That way your error handlers don't interrupt your normal flow of execution as exceptions do.
You still can interrupt the flow of your program, but you have to do that explicitly. There is a utility handler `exc_to_box`
that can be useful:

```python
from rescue import Box, bind, box_exc, unwrap

# a container for a potential error
box: Box[ValueError] = Box()

even_x = unwrap(
  bind(echo_even(1), box_exc(ValueError, box, default=0))
)

if box.content is not None:
  # here you know that `echo_even(1)` call produced an error and can act accordingly
  pass
```

Another great thing about handlers is that they themselves can be generator functions. In the case of turning a generator function into a handler you don't
need to wrap it so instead of `wrap_into_exc_handler` we use `exc_handler`:

```python
from typing import Generator
from rescue import bind, exc_handler, throw


@exc_handler(ValueError)
def throw_runtime_error(_: ValueError) -> Generator[RuntimeError, None, int]:
  yield from throw(RuntimeError("caught a ValueError"))
  return 0


reveal_type(bind(echo_even(6), throw_runtime_error))  # Revealed type is "Generator[RuntimeError, None, int]"
```
In the example above `throw_runtime_error` handled `ValueError`, but because it itself can produce a `RuntimeError` we need another handler for the generator.

## API

| API interface | Description                                                                             |
| --- |-----------------------------------------------------------------------------------------|
| [`Generator`](#Generator) | A function call that is yet to be evaluated and has error type information attached.    |
| [`yield from`](#yield-from) | Evaluates a generator inside another generator function.                                    |
| [`throw`](#throw) | A function that returns a generator that always evaluates to a given error.                 |
| [`exc_handler`](#exc_handler) | Decorates a generator function as a handler of a particular exception type.                 |
| [`wrap_into_exc_handler`](#wrap_into_exc_handler) | Decorates a regular function as a handler of a particular exception type.               |
| [`bind`](#bind) | Returns a generator with a particular exception type removed from the error type signature. |
| [`unwrap`](#unwrap) | Evaluates a generator that doesn't produce errors and returns a value.                      |

### `Generator`

Generator is an object that represents a function call that is ready to be evaluated, but evaluation is postponed until later.
To evaluate a generator you [unwrap](#unwrap) it. `Generator` is a generic type with three parameters, but `rescue` uses only two:
- the type of every possible error that can be produced by the wrapped call
- the return type of the wrapped call

A function that returns a generator becomes a **generator function** as opposed to a regular function.

> Invoking a generator function doesn't start execution, but returns a generator object.
> To actually call start the execution you should [unwrap](#unwrap) it.

---

### `yield from`

```python
from typing import Generator


def mul_even(x: int, n: int) -> Generator[ValueError, None, int]:
  value = yield from echo_even(x)
  return value * n
```

`yield from` takes a `Generator` object and evaluates it until it either returns successfully or yields an exception.
`yield from` returns a value, but any error that occurs is passed to an appropriate handler.

---

### `throw`

```python
from typing import Generator
from rescue.core import throw


def echo_even(x: int) -> Generator[ValueError, None, int]:
  if x % 2 != 0:
    yield from throw(ValueError("x must be an even number"))
  return x
```

`throw` halts the function and produces an error. It is supposed to be called via `yield from` as any other generator
function.

Think of it like `raise` that is actually reflected in the signature of a function.

> `mypy` should understand that no code is ever executed after `yield from throw(...)`, but it currently doesn't.

---

### `wrap_into_exc_handler`

```python
from rescue import wrap_into_exc_handler


@wrap_into_exc_handler(ValueError)
def return_zero(_: ValueError) -> int:
  return 0
```

`wrap_into_exc_handler` turns a function into a generator function and calls `exc_handler` on it. The following is equivalent:

```python
from typing import Generator
from rescue import exc_handler


@exc_handler(ValueError)
def return_zero(_: ValueError) -> Generator[None, None, int]:
  if False:
    yield None
  return 0
```

---

### `exc_handler`

```python
from typing import Generator
from rescue import exc_handler, throw


@exc_handler(ValueError)
def throw_runtime_error(_: ValueError) -> Generator[RuntimeError, None, int]:
  yield from throw(RuntimeError("caught a ValueError"))
  return 0
```

`exc_handler` requires an exception type and a generator function, which has a single parameter of the same type.
The return value is of type `ExcHandler`, which is a callable with extra runtime information attached.

> When `rescue` dispatches an exception at runtime it tries to find a matching handler.
> Even though handler has its parameter type annotated, this information may not be enough for `rescue` in more complex cases such as generic handlers.

---

### `unwrap`

```python
from typing import Generator
from rescue import unwrap


def add_one(x: int) -> Generator[None, None, int]:
  if False:
    yield None
  return x + 1


assert unwrap(add_one(5)) == 6
```

`unwrap` evaluates a generator, but it only accepts the ones that have `None` as the error type argument.
You can [bind](#bind) error handlers to a generator to reduce its error type to `None`.

---

## Caveats

- exceptions are great at interrupting execution, so if you can't recover from an error then just raise an exception
- `bind` is implemented via a mypy plugin, so you can't write code that is generic over arguments to `bind`
- `async/await` is not supported, because [yield from doesn't work with async](https://www.python.org/dev/peps/pep-0525/#asynchronous-yield-from)

### `asyncio` support

It's possible to use `fiasko` with `asyncio` code, but:
- you must avoid `async/await` syntax
- you must annotate your top-level main function with `Generator[None, None, None]`
- you must not call `unwrap` on async generator functions

I don't think it's worth it, but here's an example:

```python
import asyncio
import types
from typing import Any, Dict, Generator
import httpx
from rescue import bind, throw, wrap_into_exc_handler


@types.coroutine
def safe_get(
        url: str
) -> Generator[httpx.HTTPStatusError, None, Dict[str, Any]]:
  client = httpx.AsyncClient()
  resp = yield from client.get(url)
  yield from client.aclose()
  try:
    resp.raise_for_status()
  except httpx.HTTPStatusError as e:
    yield from throw(e)
  return resp.json()


@types.coroutine
def main() -> Generator[None, None, None]:
  @wrap_into_exc_handler(httpx.HTTPStatusError)
  def return_empty_on_err(_: httpx.HTTPStatusError) -> Dict[str, Any]:
    return {}

  value = yield from bind(safe_get("https://example.com"), return_empty_on_err)


asyncio.run(main())

```

## Rationale

Python makes heavy use of exceptions due to its _ask for forgiveness not permission_ philosophy. But exceptions have
specific flaws that `rescue` tries to address:

- exceptions hurt our ability for local reasoning
- exceptions transfer control in a hard to track way

> You can read more about different ways to model errors and their trade-offs in the [section with reading materials](#Further-reading).

### Ability to reason locally

> With the phrase “local reasoning”, I’m referring to the ability to understand the behavior (and thereby, the correctness) of a routine by examining the routine itself rather than examining the entire system.
>
> -- [Unyielding](https://glyph.twistedmatrix.com/2014/02/unyielding.html)

The benefit from annotating types is twofold:

- we can see the interface from the signature (that can also be achieved with documentation)
- `mypy` guarantees that the implementation actually conforms to the interface

Sadly, exceptions are too prevalent in Python to be reflected in the type signature, which means:

- there is no way of telling what exceptions a function can raise
- there is no difference between forgetting to handle an exception and doing so intentionally

It seems that the former question has a solution – documentation. But for the documentation to be a reliable solution it must be
reliably updated with the code and people must reliably read it. Humans are not good at being reliable, that's why there
is a type of error called after us.

So the only real reliable solution is to read the implementation of every function we use. We also should not forget
that any call of any other function can raise an exception, so we should read the implementation of **the entire call
tree**. And that's the point when we lose our ability for local reasoning.

### Predictable control flow

In Python the control flow is structured, which means you can follow it with your eyes from one line to the next. Even
though `if` statements and `for` loops can skip some lines, they are bounded by the scope (be it function or module).
The only ways to jump between scopes are:

- to call a function (push onto the call stack)
- to return a value (pop from the call stack)

The call stack makes it trivial to follow control flow because control eventually returns to the call site.

Except exceptions don’t respect the control flow of your program. When we raise an exception the control is
transferred _somewhere_ up the call stack, but not to the call site. This adds a dimension to the structure of our code
that we have to keep track of. The inability to follow the execution sequence can lead to corrupted state and lacking
test coverage.

## Further reading

- [The Error Model](http://joeduffyblog.com/2016/02/07/the-error-model/) by Joe Duffy
- [Concurrent Programming with Effect Handlers](https://github.com/ocamllabs/ocaml-effects-tutorial) by Daniel
  Hillerström and KC Sivaramakrishnan
- [An Introduction to Algebraic Effects and Handlers](https://www.eff-lang.org/handlers-tutorial.pdf) by Matija Pretnar
- [Introduction to Programming with Shift and Reset](http://pllab.is.ocha.ac.jp/~asai/cw2011tutorial/main-e.pdf) by
  Kenichi Asai and Oleg Kiselyov
- [Yield: Mainstream Delimited Continuations](https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.398.9600&rep=rep1&type=pdf)
  by Roshan P. James and Amr Sabry
- [A Tour of Koka](https://koka-lang.github.io/koka/doc/book.html#tour) by Daan Leijen
- [mypy and error handling](https://beepb00p.xyz/mypy-error-handling.html) by karlicoss
- [Python exceptions considered an anti-pattern](https://sobolevn.me/2019/02/python-exceptions-considered-an-antipattern) by Nikita Sobolev
