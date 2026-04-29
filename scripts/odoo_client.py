"""Cliente XMLRPC mínimo para Odoo (uso desde GitHub Actions).

Variables de entorno requeridas:
  ODOO_URL       https://bootandwork-bootodoo2.odoo.com
  ODOO_DB        nombre de la base de datos
  ODOO_USER      email del usuario (apm@industrialshields.com)
  ODOO_PASSWORD  API Key generada en Odoo (NO password real)
"""
import os
import xmlrpc.client


class Odoo:
    def __init__(self):
        self.url = os.environ["ODOO_URL"].rstrip("/")
        self.db = os.environ["ODOO_DB"]
        self.user = os.environ["ODOO_USER"]
        self.password = os.environ["ODOO_PASSWORD"]
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common")
        self.uid = common.authenticate(self.db, self.user, self.password, {})
        if not self.uid:
            raise RuntimeError("Odoo authentication failed (check ODOO_USER/PASSWORD)")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object")

    def execute(self, model, method, args, kwargs=None):
        return self.models.execute_kw(
            self.db, self.uid, self.password, model, method, args, kwargs or {}
        )

    def search_read(self, model, domain=None, fields=None, limit=None, offset=0, order=None):
        kw = {"offset": offset}
        if fields is not None:
            kw["fields"] = fields
        if limit is not None:
            kw["limit"] = limit
        if order is not None:
            kw["order"] = order
        return self.execute(model, "search_read", [domain or []], kw)

    def write(self, model, ids, values):
        return self.execute(model, "write", [ids, values])

    def read(self, model, ids, fields=None):
        return self.execute(model, "read", [ids], {"fields": fields} if fields else {})

    def post_log_note(self, model, record_id, body):
        return self.execute(
            model, "message_post",
            [[record_id]],
            {"body": body, "message_type": "comment"}
        )
