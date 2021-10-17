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

## Rationale
I really (and I mean **really**) enjoy when type checker catches a mistake before I even run the code. That gratification makes you feel the benefits of type annotating as much of your code as possible. And we type annotate almost any codebase in its entirety, but with one exception: _exceptions_.

Python makes heavy use of exceptions due to its _ask for forgiveness not permission_ philosophy. But exceptions have specific flaws that `enact` tries to address:
- exceptions hurt our ability for local reasoning
- exceptions transfer control in a hard to track way

Let me explain.

### Local reasoning
> With the phrase “local reasoning”, I’m referring to the ability to understand the behavior (and thereby, the correctness) of a routine by examining the routine itself rather than examining the entire system.
>
> -- [Unyielding](https://glyph.twistedmatrix.com/2014/02/unyielding.html)

Every function provides an interface, for example:
```python

def echo_even(x):
    if x % 2 != 0:
        raise ValueError("x must be an even number")
    return x
 ```
 
We are supposed to call `echo_even` with an even integer, but how are we supposed to know that? In this simple case we can read the code, but not every function is that simple and besides isn't that the point of abstraction – to allow us to to use something without getting into internal details? That's where typing can help us:
```python
def echo_even(x: int) -> int:
    if x % 2 != 0:
        raise ValueError("x must be an even number")
    return x
 ```
 The benefit is twofold:
 - we can see the interface from the signature (that can also be achieved with documentation)
 - we are reassured by the type checker that the implementation actually conforms to the interface

If I try and use the return value from `echo_even` as a `str`, type checker will catch that mistake. But not every mistake can be described with types, let us write another function:
```python
def echo_even_or_zero(x: int) -> int:
    value = echo_even(x)
    return value
```
Did I mean to not handle `ValueError` here or did I just forget? How can users of `echo_even_or_zero` know what exceptions they should expect and catch?

It seems that the latter question has a solution – documentation. But for the documentation to be reliable it must reliably change with the code and people must reliably read it. Humans are not good at being reliable, that's why it's called _human_ error.

So the only real reliable solution is to read the implementation of every function we use. And when we do that we should remember that any call of any other function can raise an exception, so we should read the implementation of **the entire call tree**. And that's how our ability for local reasoning goes down the drain.

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
