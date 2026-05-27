"""
.calc <выражение> — безопасный калькулятор
Пример: .calc 2+2*10  →  22
"""
import ast
import operator
import logging

logger = logging.getLogger(__name__)

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Защита от чисел-монстров (10**100 уже считается долго)
_MAX_NUM = 10 ** 100


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        # ast.Constant теперь покрывает и числа, и строки, и None — пропускаем только числа
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if abs(node.value) > _MAX_NUM:
                raise ValueError("Число слишком большое")
            return node.value
        raise ValueError("Разрешены только числа")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if not op:
            raise ValueError("Неизвестная операция")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        # Защита от взрыва: ограничиваем размер показателя и базы
        if type(node.op) is ast.Pow:
            if abs(right) > 100 or abs(left) > 10 ** 10:
                raise ValueError("Степень слишком большая")
        result = op(left, right)
        if isinstance(result, (int, float)) and abs(result) > _MAX_NUM:
            raise ValueError("Результат слишком большой")
        return result
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if not op:
            raise ValueError("Неизвестная унарная операция")
        return op(_safe_eval(node.operand))
    raise ValueError("Недопустимое выражение")


async def calc_command(event):
    try:
        args = event.raw_text.split(None, 1)
        if len(args) < 2:
            await event.edit("🧮 Использование: `.calc 2+2*10`")
            return

        expr = args[1].strip().replace("^", "**").replace(",", ".")
        if len(expr) > 200:
            await event.edit("❌ Выражение слишком длинное")
            return

        tree = ast.parse(expr, mode='eval')
        result = _safe_eval(tree.body)

        # Красивый вывод
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        try:
            formatted = f"{result:,}".replace(",", " ") if abs(result) >= 1000 else str(result)
        except (TypeError, ValueError):
            formatted = str(result)

        await event.edit(f"🧮 `{expr}` = **{formatted}**")
    except ZeroDivisionError:
        await event.edit("❌ Деление на ноль")
    except (SyntaxError, ValueError) as e:
        await event.edit(f"❌ Ошибка выражения: {e}")
    except OverflowError:
        await event.edit("❌ Результат слишком большой")
    except Exception as e:
        logger.error(f"calc_command error: {e}", exc_info=True)
        await event.edit("❌ Ошибка вычисления")
