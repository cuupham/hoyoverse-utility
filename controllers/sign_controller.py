from concurrent.futures import ThreadPoolExecutor, as_completed


def fetch_sign_status(api) -> tuple[int, dict[str, str | int]]:
    response = api.get_sign_info()
    retcode = response['retcode']
    
    if retcode != 0:
        return -1, response

    is_signed = response.get('data', {}).get('is_sign', False)
    return (1 if is_signed else 0, {'retcode': retcode, 'message': response.get('message', '')})

def handle_sign_in(api) -> dict[str, str | int]:
    status, response = fetch_sign_status(api)

    if status == 0:
        result = api.sign()
        return {
            'status': 'Done',
            'retcode': result['retcode'],
            'message': result.get('message', '')
        }
    
    if status == 1:
        return {
            'status': 'Already signed-in',
            **response
        }

    return {
        'status': 'Error',
        **response
    }

def multi_sign_in(apis):
    print(' CHECK-IN '.center(60, '='))

    result = { acc: {} for acc in apis }

    tasks = [
        (acc_name, game_key, api)
        for acc_name, games in apis.items()
        for game_key, api in games.items()
    ]

    with ThreadPoolExecutor(max_workers=15) as executor:
        future_map = {
            executor.submit(handle_sign_in, api): (acc_name, game_key)
            for acc_name, game_key, api in tasks
        }

        for future in as_completed(future_map):
            acc_name, game_key = future_map[future]
            result[acc_name][game_key] = future.result()
    
    for acc_name in apis:
        print(f'« {acc_name} »')
        for game_key, res in result[acc_name].items():
            print(f'{f"[{game_key}]":<5} → {res}')

    print()