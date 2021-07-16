"""Class decorators and other helpers.

Contains class decorators and other helper functions, for example,
to quickly add a range of Numba-compiled functions to the class."""

import numpy as np
import inspect

from vectorbt import _typing as tp
from vectorbt.utils import checks
from vectorbt.utils.config import merge_dicts, get_func_kwargs
from vectorbt.base.array_wrapper import Wrapping


WrapperFuncT = tp.Callable[[tp.Type[tp.T]], tp.Type[tp.T]]
NBFuncInfoT = tp.Tuple[str, tp.Callable, bool]


def add_nb_methods(nb_funcs: tp.Iterable[NBFuncInfoT], module_name: tp.Optional[str] = None) -> WrapperFuncT:
    """Class decorator to wrap Numba functions methods of an accessor class.

    `nb_funcs` should contain tuples each of:

    * target function name
    * Numba function, and
    * whether it's reducing.

    Requires the instance to subclass `vectorbt.base.array_wrapper.Wrapping`."""

    def wrapper(cls: tp.Type[tp.T]) -> tp.Type[tp.T]:
        checks.assert_subclass(cls, Wrapping)

        for info in nb_funcs:
            checks.assert_type(info, tuple)

            if len(info) == 3:
                fname, nb_func, is_reducing = info
            else:
                raise ValueError("Each tuple should contain 3 elements")

            def nb_method(self,
                          *args,
                          _fname: str = fname,
                          _nb_func: tp.Callable = nb_func,
                          _is_reducing: bool = is_reducing,
                          wrap_kwargs: tp.KwargsLike = None,
                          **kwargs) -> tp.SeriesFrame:
                default_kwargs = get_func_kwargs(nb_func)

                if '_1d' in _nb_func.__name__:
                    # One-dimensional array as input
                    a = _nb_func(self.to_1d_array(), *args, **{**default_kwargs, **kwargs})
                    if _is_reducing:
                        wrap_kwargs = merge_dicts(dict(name_or_index=_fname), wrap_kwargs)
                        return self.wrapper.wrap_reduced(a, **wrap_kwargs)
                    return self.wrapper.wrap(a, **merge_dicts({}, wrap_kwargs))
                else:
                    # Two-dimensional array as input
                    a = _nb_func(self.to_2d_array(), *args, **{**default_kwargs, **kwargs})
                    if _is_reducing:
                        wrap_kwargs = merge_dicts(dict(name_or_index=_fname), wrap_kwargs)
                        return self.wrapper.wrap_reduced(a, **wrap_kwargs)
                    return self.wrapper.wrap(a, **merge_dicts({}, wrap_kwargs))

            # Replace the function's signature with the original one
            sig = inspect.signature(nb_func)
            self_arg = tuple(inspect.signature(nb_method).parameters.values())[0]
            sig = sig.replace(parameters=(self_arg,) + tuple(sig.parameters.values())[1:])
            nb_method.__signature__ = sig
            if module_name is not None:
                nb_method.__doc__ = f"See `{module_name}.{nb_func.__name__}`"
            else:
                nb_method.__doc__ = f"See `{nb_func.__name__}`"
            setattr(cls, fname, nb_method)
        return cls

    return wrapper


NPFuncInfoT = tp.Tuple[str, tp.Callable]
BinaryTranslateFuncT = tp.Callable[[tp.Any, tp.Any, tp.Callable], tp.SeriesFrame]


def add_binary_magic_methods(np_funcs: tp.Iterable[NPFuncInfoT], translate_func: BinaryTranslateFuncT) -> WrapperFuncT:
    """Class decorator to add binary magic methods using NumPy to the class."""

    def wrapper(cls: tp.Type[tp.T]) -> tp.Type[tp.T]:
        for fname, np_func in np_funcs:
            def magic_func(self, other, _np_func=np_func):
                return translate_func(self, other, _np_func)

            setattr(cls, fname, magic_func)
        return cls

    return wrapper


UnaryTranslateFuncT = tp.Callable[[tp.Any, tp.Callable], tp.SeriesFrame]


def add_unary_magic_methods(np_funcs: tp.Iterable[NPFuncInfoT], translate_func: UnaryTranslateFuncT) -> WrapperFuncT:
    """Class decorator to add unary magic methods using NumPy to the class."""

    def wrapper(cls: tp.Type[tp.T]) -> tp.Type[tp.T]:
        for fname, np_func in np_funcs:
            def magic_func(self, np_func=np_func):
                return translate_func(self, np_func)

            setattr(cls, fname, magic_func)
        return cls

    return wrapper


binary_magic_methods = [
    # comparison ops
    ('__eq__', np.equal),
    ('__ne__', np.not_equal),
    ('__lt__', np.less),
    ('__gt__', np.greater),
    ('__le__', np.less_equal),
    ('__ge__', np.greater_equal),
    # arithmetic ops
    ('__add__', np.add),
    ('__sub__', np.subtract),
    ('__mul__', np.multiply),
    ('__pow__', np.power),
    ('__mod__', np.mod),
    ('__floordiv__', np.floor_divide),
    ('__truediv__', np.true_divide),
    ('__radd__', lambda x, y: np.add(y, x)),
    ('__rsub__', lambda x, y: np.subtract(y, x)),
    ('__rmul__', lambda x, y: np.multiply(y, x)),
    ('__rpow__', lambda x, y: np.power(y, x)),
    ('__rmod__', lambda x, y: np.mod(y, x)),
    ('__rfloordiv__', lambda x, y: np.floor_divide(y, x)),
    ('__rtruediv__', lambda x, y: np.true_divide(y, x)),
    # mask ops
    ('__and__', np.bitwise_and),
    ('__or__', np.bitwise_or),
    ('__xor__', np.bitwise_xor),
    ('__rand__', lambda x, y: np.bitwise_and(y, x)),
    ('__ror__', lambda x, y: np.bitwise_or(y, x)),
    ('__rxor__', lambda x, y: np.bitwise_xor(y, x))
]

unary_magic_methods = [
    ('__neg__', np.negative),
    ('__pos__', np.positive),
    ('__abs__', np.absolute),
    ('__invert__', np.invert)
]
