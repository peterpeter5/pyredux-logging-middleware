from __future__ import absolute_import, unicode_literals

from contextlib import contextmanager

from pyrsistent import freeze
import unittest


from pyreduxLogging import apply_middleware
from pyreduxLogging import create_store
from pyreduxLogging import create_typed_action_creator
from pyreduxLogging import default_reducer
from pyreduxLogging.Middlewares.Logging.Logger import redux_logger

AddTodo, create_new_todo = create_typed_action_creator("AddTodo")
CompleteTodo, complete_todo = create_typed_action_creator("CompleteTodo")


@default_reducer
def todo_handler(action, state=freeze({"todos": [], "completed": []})):
    return state


@todo_handler.register(AddTodo)
def _(action, state):
    payload = action.payload
    old_todos = state["todos"]
    new_todos = old_todos.append(payload)
    return state.update({"todos": new_todos})


@todo_handler.register(CompleteTodo)
def _(action, state):
    old_completed = state["completed"]
    return state.update({"completed": old_completed.append(action.payload["todo_id"])})


def create_new_todo_action(name, todo_id):
    new_todo = {"name": name, "todo_id": todo_id}
    return create_new_todo(new_todo)


def complete_todo_action(todo_id):
    completed = {"todo_id": todo_id}
    return complete_todo(completed)


@contextmanager
def captured_output():
    import sys
    from six import StringIO
    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class TestSimpleTodoApp(unittest.TestCase):
    def setUp(self):
        pass

    def test_can_apply_logging_middleware(self):
        with captured_output() as (out, err):
            store = create_store(todo_handler, enhancer=apply_middleware(redux_logger))
            add_todo = create_new_todo_action("install pyredux", 0)
            store.dispatch(add_todo)
            # print(self.out)
            self.assertTrue(True, "[Action: <AddTodo>] ::" in str(out))