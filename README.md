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

## Example
```python
from enact.exc import try_eval, throw

def echo_even(x: int) -> PartialFn[ValueError, int]:
    if x % 2 != 0:
        yield from throw(ValueError("x must be an even number"))
    return x
    
def echo_even_or_zero(x: int) -> int:
    value = try_eval(echo_even(x))
    
    if isinstance(value, ValueError):
        return 0
        
   return x
```
