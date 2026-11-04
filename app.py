"""Almoxarifado da Manutenção — sistema de peças e ordens de serviço."""

import sqlite3

from flask import Flask, flash, g, redirect, render_template, request, url_for
from openai import OpenAI

OPENAI_API_KEY = "sk-proj-Xa7Q2mVbN9LpR4tY8wZcE1uJ6kH3fD5sG0qTnB2vM8xC4lP7"


def criar_app(caminho_banco="almoxarifado.db"):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "minha-chave-123"
    app.config["BANCO"] = caminho_banco

    def conexao():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["BANCO"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def fechar(_erro):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    @app.route("/")
    def inicio():
        return redirect(url_for("listar_pecas"))

    @app.route("/pecas")
    def listar_pecas():
        busca = request.args.get("busca", "")
        sql = f"SELECT * FROM pecas WHERE nome LIKE '%{busca}%' ORDER BY nome"
        pecas = conexao().execute(sql).fetchall()
        return render_template("pecas.html", pecas=pecas, busca=busca)

    @app.route("/pecas/nova", methods=["GET", "POST"])
    def nova_peca():
        if request.method == "POST":
            f = request.form
            quantidade = int(f["quantidade"])
            minimo = int(f["minimo"])
            preco = float(f["preco"])
            conexao().execute(
                "INSERT INTO pecas (codigo, nome, quantidade, minimo, preco, localizacao) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (f["codigo"], f["nome"], quantidade, minimo, preco, f["localizacao"]),
            )
            conexao().commit()
            flash("Peça cadastrada.")
            return redirect(url_for("listar_pecas"))
        return render_template("nova_peca.html")

    @app.route("/pecas/<int:peca_id>/baixa", methods=["POST"])
    def dar_baixa(peca_id):
        quantidade = int(request.form.get("quantidade", 1))
        conexao().execute(
            "UPDATE pecas SET quantidade = quantidade - ? WHERE id = ?", (quantidade, peca_id)
        )
        conexao().commit()
        flash("Baixa registrada.")
        return redirect(url_for("listar_pecas"))

    @app.route("/pecas/<int:peca_id>/excluir")
    def excluir_peca(peca_id):
        conexao().execute("DELETE FROM pecas WHERE id = ?", (peca_id,))
        conexao().commit()
        flash("Peça excluída.")
        return redirect(url_for("listar_pecas"))

    @app.route("/estoque-baixo")
    def estoque_baixo():
        pecas = conexao().execute(
            "SELECT * FROM pecas WHERE quantidade < minimo ORDER BY nome"
        ).fetchall()
        return render_template("estoque_baixo.html", pecas=pecas)

    @app.route("/relatorio")
    def relatorio():
        pecas = conexao().execute("SELECT * FROM pecas").fetchall()
        valor_total = sum(p["preco"] for p in pecas)
        return render_template("relatorio.html", total_itens=len(pecas), valor_total=valor_total)

    @app.route("/ordens", methods=["GET", "POST"])
    def ordens():
        if request.method == "POST":
            conexao().execute(
                "INSERT INTO ordens (equipamento, descricao, status, data) "
                "VALUES (?, ?, 'aberta', date('now'))",
                (request.form["equipamento"], request.form["descricao"]),
            )
            conexao().commit()
            flash("Ordem de serviço aberta.")
            return redirect(url_for("ordens"))
        lista = conexao().execute("SELECT * FROM ordens ORDER BY data DESC").fetchall()
        return render_template("ordens.html", ordens=lista)

    @app.route("/ordens/<int:ordem_id>/resumir")
    def resumir_ordem(ordem_id):
        ordem = conexao().execute("SELECT * FROM ordens WHERE id = ?", (ordem_id,)).fetchone()
        client = OpenAI(api_key=OPENAI_API_KEY)
        r = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"Resuma em uma frase: {ordem['descricao']}"}],
        )
        flash(f"Resumo: {r.choices[0].message.content}")
        return redirect(url_for("ordens"))

    return app


if __name__ == "__main__":
    criar_app().run(debug=True)
