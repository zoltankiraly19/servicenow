from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Globális változók
current_caller_id = None  # A caller_id (sys_id) tárolása
access_token_global = None  # A megszerzett token tárolása
current_user_id = None  # A user_id (felhasználónév) tárolása


@app.route('/get_token', methods=['POST'])
def get_token():
    global access_token_global, current_user_id  # Globális token és user_id változó
    data = request.json
    auth_data = {
        'grant_type': 'password',
        'client_id': '45f3f2fb2ead4928ab994c64c664dfdc',
        'client_secret': 'fyHL1.@d&7',
        'username': data.get('username'),
        'password': data.get('password')
    }

    response = requests.post('https://dev227667.service-now.com/oauth_token.do', data=auth_data)

    if response.status_code == 200:
        access_token = response.json().get('access_token')
        access_token_global = access_token  # A token globálisan tárolódik
        current_user_id = data.get('username')  # A felhasználónév globálisan tárolódik
        return jsonify({"access_token": access_token}), 200
    else:
        return jsonify({"error": "Authentication failed", "details": response.text}), 400


@app.route('/get_servicenow_data', methods=['POST'])
def get_servicenow_data():
    global current_caller_id, access_token_global, current_user_id  # Globális token és user_id változók

    if access_token_global is None:
        return jsonify({"error": "Token not available. Please authenticate first."}), 400

    if current_user_id is None:
        return jsonify({"error": "User ID not available. Please authenticate first."}), 400

    headers = {
        'Authorization': f'Bearer {access_token_global}',  # A globális token használata
        'Content-Type': 'application/json'
    }

    # Lekérjük a felhasználó sys_id-ját a globálisan tárolt user_name alapján
    response_user = requests.get(
        f"https://dev227667.service-now.com/api/now/table/sys_user?sysparm_query=user_name={current_user_id}",
        headers=headers)

    caller_id = None
    result_user_id = None  # Felhasználó user_id (a sys_user táblából)
    result_name = None  # Felhasználó name (a sys_user táblából)

    if response_user.status_code == 200:
        users = response_user.json().get('result', [])
        if users:
            caller_id = users[0].get("sys_id")  # Csak a sys_id-t kapjuk vissza
            current_caller_id = caller_id  # Globálisan elmentjük a sys_id-t
            result_user_id = users[0].get("user_name")  # User_name (user_id) a válaszban
            result_name = users[0].get("name")  # Hozzátartozó name

    # Assignment groupok lekérdezése
    response_groups = requests.get('https://dev227667.service-now.com/api/now/table/sys_user_group', headers=headers)
    group_data = []
    if response_groups.status_code == 200:
        groups = response_groups.json().get('result', [])
        group_data = [{"name": group["name"], "sys_id": group["sys_id"]} for group in groups]

    # Priority lekérdezés
    response_priorities = requests.get(
        'https://dev227667.service-now.com/api/now/table/sys_choice?sysparm_query=name=incident^element=priority',
        headers=headers)
    priority_data = []
    if response_priorities.status_code == 200:
        priorities = response_priorities.json().get('result', [])
        priority_data = [{"label": priority["label"], "value": priority["value"]} for priority in priorities]

    return jsonify({
        "caller_id": caller_id,
        "user_id": result_user_id,  # Hozzáadjuk a user_id-t (user_name)
        "name": result_name,  # Hozzáadjuk a felhasználó nevét
        "assignment_groups": group_data,
        "priorities": priority_data
    }), 200

@app.route('/create_ticket', methods=['POST'])
def create_ticket():
    global current_caller_id  # Automatikusan beállítjuk a felhasználó sys_id-ját (caller_id)
    global access_token_global  # Globális token változó

    if access_token_global is None:
        return jsonify({"error": "Token not available. Please authenticate first."}), 400

    data = request.json

    headers = {
        'Authorization': f'Bearer {access_token_global}',  # A globális token használata
        'Content-Type': 'application/json'
    }

    ticket_data = {
        "short_description": data.get('short_description'),
        "assignment_group": data.get('assignment_group_sys_id'),
        "priority": data.get('priority'),
        "caller_id": current_caller_id  # A globális sys_id-t használjuk itt
    }

    response = requests.post('https://dev227667.service-now.com/api/now/table/incident', json=ticket_data,
                             headers=headers)

    if response.status_code == 201:
        return jsonify({"message": "Ticket created successfully",
                        "ticket_number": response.json().get('result', {}).get('number')}), 201
    else:
        return jsonify({"error": "Failed to create ticket", "details": response.text}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
