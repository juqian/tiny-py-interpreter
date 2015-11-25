from enum import Enum
from AST.ast import Statement, Expression
from AST.expr import AddOp, SubOp, MultOp, DivOp, ModOp, BitAndOp, BitOrOp, BitXorOp, LshiftOp, RshiftOp, Name

import runtime.Memory
import runtime.Errors

"""
# Function definition.
#   @name - text name of the function
#   @args - list of arguments (just names)
#   @body - list of statements, which form functions body
#
# Every function has name which is written to the outer namespace.
# For the top-level function definitions, the outer namespace is the global namespace.
# For nested functions its the namespace of the outer function.
#
# Our way to implement name scoping is to set current namespace during the evaluation of ANY *STATEMENT*
# Actually, we'll need to set the new (and then back the old one) when evaluating only functions,
# as there are no scoping rules for other statements; thus, @Name expression will need to check
# only single global variable - current namespace, and function calls will switch scopes.
#
# This solution is far from perfect. However, it just works as there is no need for modules.
# Implementing modules will require providing each @Name node an ability to get a proper namespace.
"""
class FunctionDef(Statement):
    def __init__(self, name:str, args:list, body:list):
        super().__init__()
        self.name = name
        self.args = args
        self.body = body

    def getNamespace(self) -> runtime.Memory.Namespace:
        return runtime.Memory.CurrentNamespace

    def eval(self) -> None:

        previousNamespace = self.getNamespace()
        namespace = runtime.Memory.Namespace(outerScope=previousNamespace)

        def container(*args):
            runtime.Memory.CurrentNamespace = namespace

            if len(args) != len(self.args):
                message = "%s() takes %d positional arguments but %d were given" % \
                          (self.name, len(self.args), len(args))
                raise runtime.Errors.TypeError(message)

            for pair in zip (self.args, args):
                namespace.set(name=pair[0], value=pair[1])

            returnValue = None

            for stmt in self.body:
                res = stmt.eval()
                if isinstance(res, ControlFlowMark):
                    if res.type == ControlFlowMark.Type.Return:
                        if res.toEval != None:
                            returnValue = res.toEval.eval()
                        break

            runtime.Memory.CurrentNamespace = previousNamespace
            return returnValue

        # Finally, write the function container to the memory.
        # Call to the container will trigger eval of function body
        previousNamespace.set(self.name, container)
        return None


"""
# An if statement.
#    @test holds a single node, such as a Compare node.
#    @body and orelse each hold a list of nodes.
#
# @elif clauses don’t have a special representation in the AST, but rather
# appear as extra If nodes within the orelse section of the previous one.
#
# Optional clauses such as @else are stored as an empty list if they’re not present.
"""
class IfStmt(Statement):
    def __init__(self, test, body:[], orelse:[]):
        super().__init__()
        self.test = test
        self.body = body
        self.orelse = orelse

    def eval(self):
        test = self.test.eval()
        result = []

        for stmt in self.body if (test == True) else self.orelse:
            evalResult = stmt.eval()

            if isinstance(evalResult, ControlFlowMark):
                if evalResult.type != ControlFlowMark.Type.Pass:
                    return evalResult

            if type(evalResult) is list:
                result += evalResult
            else:
                result.append(evalResult)

        return result


"""
# An while statement.
#    @test holds a single node, such as a @Compare node.
#    @body and @orelse each hold a list of nodes.
#
# @orelse is not used as it is not present in grammar.
"""
class WhileStmt(Statement):
    def __init__(self, test, body:[], orelse:[]):
        super().__init__()
        self.test = test
        self.body = body

    def eval(self):
        result = []

        while self.test.eval() == True:
            shouldBreak = False
            for stmt in self.body:
                evalResult = stmt.eval()

                if isinstance(evalResult, ControlFlowMark):
                    if evalResult.type == ControlFlowMark.Type.Break:
                        shouldBreak = True
                        break
                    elif evalResult.type == ControlFlowMark.Type.Continue:
                        break
                    elif evalResult.type == ControlFlowMark.Type.Pass:
                        pass
                    elif evalResult.type == ControlFlowMark.Type.Return:
                        return evalResult

                if type(evalResult) is list:
                    result += evalResult
                else:
                    result.append(evalResult)
            if shouldBreak:
                break

        return result

"""
# An assignment.
#   @targets is a list of nodes,
#   @value is a single node.
#
# Multiple nodes in targets represents assigning the same value to each.
# Unpacking is represented by putting a Tuple or List within targets.
"""
class AssignStmt(Statement):
    def __init__(self, target, value:Expression):
        super().__init__()
        self.target = target
        self.value = value

    def eval(self) -> None:
        lValue = self.target.eval()
        rValue = self.value.eval()
        runtime.Memory.CurrentNamespace.set(name=lValue, value=rValue)



class AugAssignStmt(AssignStmt):
    opTable = {
        '+=' : AddOp,
        '-=' : SubOp,
        '*=' : MultOp,
        '/=' : DivOp,
        '%=' : ModOp,
        '&=' : BitAndOp,
        '|=' : BitOrOp,
        '^=' : BitXorOp,
        '<<=' : LshiftOp,
        '>>=' : RshiftOp,
    }

    def __init__(self, name, value, op):
        nameNodeLoad  = Name(id=name, ctx=Name.Context.Load)
        nameNodeStore = Name(id=name, ctx=Name.Context.Store)

        binOp = AugAssignStmt.opTable[op](left=nameNodeLoad, right=value)
        super().__init__(target=nameNodeStore, value=binOp)


"""
# Control flow statements.
# Each statement returns corresponding @ControlFlowMark as a result of evaluation.
# Compound statements are checking whether evaluation result is a such mark, and react accordingly.
"""
class ControlFlowStmt(Statement):
    pass


class ReturnStmt(ControlFlowStmt):
    def __init__(self, expr):
        super().__init__()
        self.expr = expr

    def eval(self):
        return ControlFlowMark(ControlFlowMark.Type.Return, self.expr)


class PassStmt(ControlFlowStmt):
    def eval(self):
        return ControlFlowMark(ControlFlowMark.Type.Pass)


class ContinueStmt(ControlFlowStmt):
    def eval(self):
        return ControlFlowMark(ControlFlowMark.Type.Continue)


class BreakStmt(ControlFlowStmt):
    def eval(self):
        return ControlFlowMark(ControlFlowMark.Type.Break)


class ControlFlowMark:

    class Type(Enum):
        Return   = 1
        Break    = 2
        Continue = 3
        Pass     = 4

    def __init__(self, type, toEval=None):
        self.type = type
        self.toEval = toEval






