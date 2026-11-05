"""Guard the read-only package boundary, independently of analytical outputs."""
import ast
from pathlib import Path
import unittest


class ReadOnlyBoundary(unittest.TestCase):
    def test_no_order_or_private_package_dependency(self):
        root=Path(__file__).resolve().parents[1]/'forex'
        for path in root.glob('*.py'):
            tree=ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node,ast.Call):
                    called=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else ''
                    self.assertNotIn(called,('order_send','order_check','place_order','submit_order'),str(path))
                    if called=='_call' and node.args and isinstance(node.args[0],ast.Constant):
                        self.assertNotIn(node.args[0].value,('order_send','order_check'),str(path))
                if isinstance(node,ast.ImportFrom):
                    self.assertFalse((node.module or '').startswith('market_ai'),str(path))
                if isinstance(node,ast.Import):
                    self.assertFalse(any(n.name.startswith('market_ai') for n in node.names),str(path))

    def test_deterministic_modules_have_no_network_or_storage_imports(self):
        root=Path(__file__).resolve().parents[1]/'forex'
        for name in ('contracts','extensions','unified','structure','strategies','research','macro','microstructure','policy'):
            tree=ast.parse((root/(name+'.py')).read_text())
            modules=[]
            for node in ast.walk(tree):
                if isinstance(node,ast.Import): modules.extend(n.name for n in node.names)
                if isinstance(node,ast.ImportFrom): modules.append(node.module or '')
            self.assertFalse(set(modules)&{'requests','httpx','socket','sqlite3','pymongo','urllib.request'},name)
