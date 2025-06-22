from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
import bcrypt
import base64

from extensions import db
from models import User, Transaction, Product
from currency import get_conversion_rate

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

@app.route('/')
def home():
    return {"message": "Digital Wallet API is running"}

# Authentication function
def authenticate():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        return None

    auth_decoded = base64.b64decode(auth_header.split(' ')[1]).decode('utf-8')
    username, password = auth_decoded.split(':')

    user = User.query.filter_by(username=username).first()
    if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None

# Register user
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'User already exists'}), 400

    hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    new_user = User(username=username, password_hash=hashed_pw.decode('utf-8'))
    db.session.add(new_user)
    db.session.commit()

    return jsonify({'message': 'User created successfully'}), 201

# Fund account
@app.route('/fund', methods=['POST'])
def fund():
    user = authenticate()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    amt = data.get('amt')

    if not amt or amt <= 0:
        return jsonify({'error': 'Amount must be greater than zero'}), 400

    user.balance += amt

    txn = Transaction(user_id=user.id, kind='credit', amt=amt, updated_bal=user.balance)
    db.session.add(txn)
    db.session.commit()

    return jsonify({'balance': user.balance}), 200

# Pay another user
@app.route('/pay', methods=['POST'])
def pay():
    user = authenticate()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    to_username = data.get('to')
    amt = data.get('amt')

    if not to_username or not amt or amt <= 0:
        return jsonify({'error': 'Invalid input'}), 400

    recipient = User.query.filter_by(username=to_username).first()
    if not recipient:
        return jsonify({'error': 'Recipient not found'}), 400

    if user.balance < amt:
        return jsonify({'error': 'Insufficient funds'}), 400

    user.balance -= amt
    recipient.balance += amt

    txn_sender = Transaction(user_id=user.id, kind='debit', amt=amt, updated_bal=user.balance)
    txn_receiver = Transaction(user_id=recipient.id, kind='credit', amt=amt, updated_bal=recipient.balance)

    db.session.add_all([txn_sender, txn_receiver])
    db.session.commit()

    return jsonify({'balance': user.balance}), 200

# Check balance
@app.route('/bal', methods=['GET'])
def balance():
    user = authenticate()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    currency = request.args.get('currency')

    if not currency:
        return jsonify({'balance': user.balance, 'currency': 'INR'}), 200

    rate = get_conversion_rate(currency)

    if not rate:
        return jsonify({'error': 'Currency API unavailable'}), 500

    converted_bal = user.balance * rate
    return jsonify({'balance': round(converted_bal, 2), 'currency': currency}), 200

# Transaction history
@app.route('/stmt', methods=['GET'])
def transaction_history():
    user = authenticate()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).all()

    return jsonify([txn.to_dict() for txn in transactions]), 200

# Add product
@app.route('/product', methods=['POST'])
def add_product():
    user = authenticate()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    name = data.get('name')
    price = data.get('price')
    description = data.get('description')

    if not name or not price or price <= 0:
        return jsonify({'error': 'Invalid product details'}), 400

    product = Product(name=name, price=price, description=description)
    db.session.add(product)
    db.session.commit()

    return jsonify({'id': product.id, 'message': 'Product added'}), 201

# List all products
@app.route('/product', methods=['GET'])
def list_products():
    products = Product.query.all()

    result = []
    for p in products:
        result.append({
            'id': p.id,
            'name': p.name,
            'price': p.price,
            'description': p.description
        })

    return jsonify(result), 200

# Buy product
@app.route('/buy', methods=['POST'])
def buy_product():
    user = authenticate()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    product_id = data.get('product_id')

    if not product_id:
        return jsonify({'error': 'Product ID is required'}), 400

    product = Product.query.get(product_id)
    if not product:
        return jsonify({'error': 'Invalid product'}), 400

    if user.balance < product.price:
        return jsonify({'error': 'Insufficient balance'}), 400

    user.balance -= product.price

    txn = Transaction(user_id=user.id, kind='debit', amt=product.price, updated_bal=user.balance)
    db.session.add(txn)
    db.session.commit()

    return jsonify({'message': 'Product purchased', 'balance': user.balance}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
