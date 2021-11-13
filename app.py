import os
from flask import Flask, jsonify, abort, request, Response
from sqlalchemy.exc import IntegrityError
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path
from flask_migrate import Migrate

BASE_DIR = Path(__file__).parent

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or f"sqlite:///{BASE_DIR / 'test.db'}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class AuthorModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32), unique=True)
    quotes = db.relationship('QuoteModel', backref='author', lazy='dynamic', cascade="all, delete-orphan")

    def __init__(self, name):
        self.name = name

    def to_dict(self):
        d = {}
        for column in self.__table__.columns:
            d[column.name] = str(getattr(self, column.name))
        return d


class QuoteModel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey(AuthorModel.id))
    text = db.Column(db.String(255), unique=False)
    rate = db.Column(db.Integer, nullable=False, server_default="0", default="1")

    def __init__(self, author, text):
        self.author_id = author.id
        self.text = text

    # def __repr__(self):
    #     return f"Quote: {self.author}/ {self.text[:15]}..."
    #
    def to_dict(self):
        d = {}
        for column in self.__table__.columns:
            d[column.name] = str(getattr(self, column.name))
        del d["author_id"]
        d["author"] = self.author.to_dict()
        return d


# Resource: Quotes

@app.route("/quotes")
def quotes_list():
    quotes = QuoteModel.query.all()
    quotes = [quote.to_dict() for quote in quotes]
    return jsonify(quotes)  # Сериализация  object --> dict --> json


@app.route("/authors/<int:author_id>/quotes/<int:quote_id>")
def get_quote(author_id, quote_id):
    quote = QuoteModel.query.get(quote_id)
    if quote is None:
        abort(404, description=f"Quote with id={id} not found")
    return jsonify(quote.to_dict())


@app.route("/authors/<int:author_id>/quotes", methods=["POST"])
def create_quote(author_id):
    new_data = request.json
    # quote = QuoteModel(new_quote["author"], new_quote["quote"])
    author = AuthorModel.query.get(author_id)
    quote = QuoteModel(author, new_data["text"])
    db.session.add(quote)
    db.session.commit()
    return jsonify(quote.to_dict()), 201


@app.route("/quotes/<int:id>", methods=["PUT"])
def edit_quote(id):
    new_data = request.json
    quote = QuoteModel.query.get(id)
    if quote:  # Если цитата найдена в базе - изменяем
        quote.author = new_data.get("author") or quote.author
        quote.text = new_data.get("text") or quote.text
        db.session.commit()
        return quote.to_dict(), 200
    else:  # Если нет - создаем новую
        new_quote = QuoteModel(**new_data)
        db.session.add(new_quote)
        db.session.commit()
        return quote.to_dict(), 201


@app.route("/quotes/<int:id>", methods=['DELETE'])
def delete(id: int):
    # delete quote with id
    quote = QuoteModel.query.get(id)
    if quote:
        db.session.delete(quote)
        db.session.commit()
        return quote.to_dict(), 200
    abort(404, description=f"Quote with id={id} not found")


# Resource: Author

@app.route("/authors", methods=["POST"])
def create_author():
    author_data = request.json
    author = AuthorModel(author_data["name"])
    db.session.add(author)
    try:
        db.session.commit()
    except IntegrityError:
        return {"error": "Name must Unique"}, 400
    return author.to_dict(), 201


if __name__ == "__main__":
    app.run(debug=True)
