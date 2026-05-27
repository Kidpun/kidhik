"""
.calc <выражение> — безопасный калькулятор
Пример: .calc 2+2*10  →  22
"""
import ast
import operator
import logging

logger = logging.getLogger(__name__)

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant):
        return node.n
    if isinstance(node, ast.BinOp):
        op = _OPS.get(type(node.op))
        if not op:
            raise ValueError("Неизвестная операция")
        left = _safe_eval(node.left)
        right = _safe_eval(node.right)
        if type(node.op) is ast.Pow and abs(right) > 100:
            raise ValueError("Степень слишком большая")
        return op(left, right)
    if isinstance(node, ast.UnaryOp):
        op = _OPS.get(type(node.op))
        if not op:
            raise ValueError("Неизвестная операция")
        return op(_safe_eval(node.operand))
    raise ValueError(f"Недопустимое выражение")


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
        formatted = f"{result:,}".replace(",", " ") if abs(result) >= 1000 else str(result)

        await event.edit(f"🧮 `{expr}` = **{formatted}**")
    except ZeroDivisionError:
        await event.edit("❌ Деление на ноль")
    except (SyntaxError, ValueError) as e:
        await event.edit(f"❌ Ошибка выражения: {e}")
    except Exception as e:
        logger.error(f"calc_command error: {e}", exc_info=True)
        await event.edit("❌ Ошибка вычисления")
