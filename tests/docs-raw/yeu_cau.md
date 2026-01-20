# Daily checkin and check redeem - Hoyoverse - List game: Genshin, Star Rail, ZZZ

## Thông tin api dùng chung  
HEADER chung: {
        "accept": "application/json, text/plain, */*",
        "accept-language": "en-US,en;q=0.9,vi-VN;q=0.8,vi;q=0.7",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36",
        "dnt": "1",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
    }

 ORIGIN = {
        "hoyolab": {
            "origin": "https://www.hoyolab.com",
            "referer": "https://www.hoyolab.com/",
        },
        "act_hoyolab": {
            "origin": "https://act.hoyolab.com",
            "referer": "https://act.hoyolab.com/",
        },
        "zenless": {
            "origin": "https://zenless.hoyoverse.com",
            "referer": "https://zenless.hoyoverse.com/",
        },
        "genshin": {
            'origin': 'https://genshin.hoyoverse.com',
            'referer': 'https://genshin.hoyoverse.com/',
        }
    }

Thông tin mỗi game: gs -> Genshin, sr -> Star Rail, zzz -> Zzz
{
        'gs': {
            'game_id': '2',
            'act_id': 'e202102251931481',
            'region': {
                'asia': 'os_asia',
                'usa': 'os_usa',
                'euro': 'os_euro',
                'tw': 'os_cht',
            },
            'game_biz': 'hk4e_global',
        },
        'sr': {
            'game_id': '6',
            'act_id': 'e202303301540311',
            'region': {
                'asia': 'prod_official_asia',
                'usa': 'prod_official_usa',
                'euro': 'prod_official_eur',
                'tw': 'prod_official_cht',
            },
            'game_biz': 'hkrpg_global'
        },
        'zzz': {
            'game_id': '8',
            'act_id': 'e202406031448091',
            'region': {
                'asia': 'prod_gf_jp',
                'usa': 'prod_gf_us',
                'euro': 'prod_gf_eu',
                'tw': 'prod_gf_sg',
            },
            'game_biz': 'nap_global'
        },
    }

Một account có thể chơi 3 game. Mỗi game có 4 server (asia, usa, euro, tw).
Điểm danh thì không phân biệt server. Còn nhập redeem code thì cần phân biệt server.
Mỗi game sẽ có live phiên bản sẽ được tặng code. Khi nhập code thì cần truyền vào uid của account, server của account và code.


## Yêu cầu
1. Trong Git actions:
- tôi nhập vào giả sử 4 cookie vào biến môi trường secret trên git action, mỗi cookie đại diện cho account của hoyoverse.

- Ví dụ:
ACC_1 = "mi18nLang=en-us; _HYVUUID=af352588-4256-4550-a54a-b6ede4b893e9; HYV_LOGIN_PLATFORM_OPTIONAL_AGREEMENT={%22content%22:[]}; DEVICEFP=73839365132; _MHYUUID=92551a29-1a7a-4869-88ba-f2e3a2681065; cookie_token_v2=v2_CAQSDGM5b3FhcTNzM2d1OBokYWYzNTI1ODgtNDI1Ni00NTUwLWE1NGEtYjZlZGU0Yjg5M2U5IOeTqcsGKJztgaEBMKqazTtCC2Jic19vdmVyc2Vh.50lqaQAAAAAB.MEYCIQDAsKKbGiIUf9fHIDuEHtLRyNlA49Y2BgU7NVC6aSuFywIhAKVSW8JbgYQ-SlNVx3Ac8qUv17ToYD9ngp5oOAfPsjiP; account_mid_v2=19ekiinc4h_hy; account_id_v2=124996906; ltoken_v2=v2_CAISDGM5b3FhcTNzM2d1OBokYWYzNTI1ODgtNDI1Ni00NTUwLWE1NGEtYjZlZGU0Yjg5M2U5IOeTqcsGKLX3x_EBMKqazTtCC2Jic19vdmVyc2Vh.50lqaQAAAAAB.MEUCIQDM6ciimQuXMlbqteVPvwORF3UqqLRi1TE596S3gOcakQIgTeEiIqdsK87LpsClGsVu8G6uRdlor5TPXn0UiMApgzI; ltmid_v2=19ekiinc4h_hy; ltuid_v2=124996906; HYV_LOGIN_PLATFORM_LIFECYCLE_ID={%22value%22:%227954a952-d031-44e4-bf96-c25922aa21b6%22}; HYV_LOGIN_PLATFORM_LOAD_TIMEOUT={}; HYV_LOGIN_PLATFORM_TRACKING_MAP={}"
ACC_2 = "cookie_2"    // giá trị tương tự cookie_1
ACC_3 = "cookie_3"    // giá trị tương tự cookie_1
ACC_4 = "cookie_4"    // giá trị tương tự cookie_1
 
2. Trong .github/workflows/ , viết:
    ...
    env:
        ACC_1: ${{ secrets.ACC_1 }}
        ACC_2: ${{ secrets.ACC_2 }}
        ACC_3: ${{ secrets.ACC_3 }}
        ACC_4: ${{ secrets.ACC_4 }}
    ...
=> sau khi git action run sẽ gắn các giá trị secret vào biến môi trường (của ubuntu)

3. Trong code:
## Main Flow:
- xây dựng hàm làm sao để lặp qua danh sách các biến môi trường secret này, và đưa ra được danh sách name: cookie còn sử dụng được, cái nào không sử dụng được thì bỏ qua:
    - hàm lấy danh sách biến môi trường secret:
        * TH trong môi trường không có biến secret account nào thì thông báo ra màn hình và dừng chương trình luôn.

    - hàm kiểm tra cookie còn sử dụng được hay không:
        API:
            method: GET
            url: 'https://bbs-api-os.hoyolab.com/community/misc/wapi/account/user_brief_info'
            headers={
                **HEADER chung,
                'x-rpc-client_type': '4',
                'x-rpc-device_id': cookies['_MHYUUID'],
                'x-rpc-hour': current_hour(),
                'x-rpc-language': 'en-us',
                'x-rpc-lrsag': '',
                'x-rpc-page_info': '{"pageName":"HomePage","pageType":"","pageId":"","pageArrangement":"","gameId":""}',
                'x-rpc-page_name': 'HomePage',
                'x-rpc-show-translated': 'false',
                'x-rpc-source_info': '{"sourceName":"UserSettingPage","sourceType":"RewardsInfo","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                'x-rpc-sys_version': 'Windows NT 10.0',
                'x-rpc-timezone': 'Asia/Bangkok',
                'x-rpc-weekday': rpc_weekday(),
            }
            cookie : tương ứng

            => repsonse sẽ trả về dạng {'retcode':..., 'message':..., 'data':...}
            Nếu api này có retcode == 0 và có 'data' chứa biến 'email_mask' chứa giá trị thì cookie này còn sống, các trường hợp ngoài 2 điều kiện này nghĩa là cookie/account đó không sử dụng được.

    - hàm duyệt qua tất cả account (cookie) (sử dụng đa luồng để cùng lúc có thể gọi loạt API chạy đỡ mất thời gian, vì API có cookie khác nhau nên không bị hạn chế gì) và kiểm tra cookie còn sử dụng được hay không rồi trả về danh sách các account còn sống. Nếu danh sách là rỗng (không có account nào) thì in ra text thông báo không có account nào và thoát chương trình luôn. (để tôi có thể thấy được kết quả khi mở trong git action ra xem lại và biết được tại sao hôm đó không điểm danh được)

- Ví dụ:
TH Lặp qua danh sách 5 account (cookie): acc thứ 3 không truy cập được do ai đó đổi mật khẩu; cookie hết hạn thì chỉ return về danh sách 4 account còn lại: acc_1, acc_2, acc_4, acc_5

TH tất cả cookie đều không sử dụng được (hết hạn; ai đó đổi mật khẩu; ...) thì return về danh sách rỗng, in ra text thông báo không có account nào và thoát chương trình luôn.


- Sau khi đã có được danh sách các account còn sống, ta sẽ duyệt qua danh sách này và thực hiện 2 công việc chính: Checkin và Check redeem code; 2 công việc này sẽ call API song song.

    Flow:
    Checkin: mỗi account sẽ có 3 luồng checkin 3 game song song (gs, sr, zzz). Ví dụ:
        1 account thì có 3 luồng song song.
        2 account thì có 6 luồng song song.
        3 account thì có 9 luồng song song.
        4 account thì sẽ có 12 luồng song song.
        5 account thì có 15 luồng song song.

    Check redeem code: Tính theo game, mỗi game khi có live phiên bản mới thì sẽ được nhà phát hành tặng:
        - Genshin: 3 redeem code (3 code khác nhau)
        - Star Rail: 3 redeem code (3 code khác nhau)
        - ZZZ: 1 redeem code (1 code)

    ZZZ có 1 code thì không nói, còn genshin với star rail có 3 code thì cần phải nhập từng code, ví dụ code 1 -> code 2 -> code 3 hay 1 -> 3 -> 2 hay 2 -> 1 -> 3,... thì đều được, miễn là 3 code này khác nhau. Mỗi lần nhập xong 1 code thì không cần biết là thành công hay thất bại, sẽ có một khoảng delay khoảng 5s rồi mới nhập tiếp được - trong 1 account(cookie).

    Ví dụ:
    TH: có 1 account, genshin có 3 code:
        - chỉ có 1 luồng:
            nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.

    TH: có 2 account, genshin có 3 code:
        - có 2 luồng:
            luồng 1: nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc 1: code 1: result, code 2: result, code 3: result và kết thúc.
            luồng 2: nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc 2: code 1: result, code 2: result, code 3: result và kết thúc.

    TH: có 1 account, genshin có 3 code, star rail có 3 code:
        - có 2 luồng:
            luồng 1: nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.
            luồng 2: nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.

    TH: có 1 account, genshin có 3 code, star rail có 3 code, zzz có 1 code:
        - có 3 luồng:
            luồng 1: nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.
            luồng 2: nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.
            luồng 3: nhập code 1, lưu thông tin acc: code 1: result và kết thúc.

    TH: có 4 account, genshin có 3 code, zzz có 1 code:
        - Chia 4 luồng:
            Luồng 1:
                acc_1 chia 2 luồng:
                    luồng 1.1 - nhập code genshin:
                        nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.
                    luồng 1.2 - nhập code zzz:
                        nhập code 1, lưu thông tin acc: code 1: result và kết thúc.
            Luồng 2:
                acc_2 chia 2 luồng:
                    luồng 2.1 - nhập code genshin:
                        nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.
                    luồng 2.2 - nhập code zzz:
                        nhập code 1, lưu thông tin acc: code 1: result và kết thúc.
            Luồng 3:
                acc_3 chia 2 luồng:
                    luồng 3.1 - nhập code genshin:
                        nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.
                    luồng 3.2 - nhập code zzz:
                        nhập code 1, lưu thông tin acc: code 1: result và kết thúc.
            Luồng 4:
                acc_4 chia 2 luồng:
                    luồng 4.1 - nhập code genshin:
                        nhập code 1 -> nghỉ 5s -> nhập code 2 -> nghỉ 5s -> nhập code 3, lưu thông tin acc: code 1: result, code 2: result, code 3: result và kết thúc.
                    luồng 4.2 - nhập code zzz:
                        nhập code 1, lưu thông tin acc: code 1: result và kết thúc.

    - Công việc Checkin:
        - Mỗi account sẽ cần check (3 game) mỗi game đã điểm danh chưa thông qua api (sẽ thực hiện 3 luồng song song - GS/SR/ZZZ):
         
        Genshin:    - Luồng 1
            ## API lấy thông tin đã điểm danh chưa:
            url: "https://sg-hk4e-api.hoyolab.com/event/sol/info"
            method: GET
            cookies: tương ứng cookie
            headers={
                **header chung,
                **ORIGIN['act_hoyolab'],
                'x-rpc-lrsag': '',
            },
            params={
                'lang': 'en-us',
                'act_id': ACT_ID tương ứng game
            }
            => response là {'retcode':..., 'message':..., 'data':...}

            Nếu "retcode" khác 0 nghĩa là api này không thành công, và "message" sẽ chứa thông báo lỗi. Mình phải thu thập lỗi này để sau còn in ra màn hình để tôi đọc mà biết lỗi gì. lưu lại account: message_lỗi và thoát hàm điểm danh gemshin.

            Nếu "retcode" == 0 thì check tiếp "data", nếu "data" chứa "is_sign" và "is_sign" == True thì account này đã điểm danh rồi. lưu lại thông tin: account: "Đã điểm danh" và thoát hàm điểm danh gemshin.

            Nếu "retcode" == 0 và "data": {"is_sign": False} thì account này chưa điểm danh và thực hiện call api submit điểm danh:

                ## API thực thi điểm danh:
                url: "https://sg-hk4e-api.hoyolab.com/event/sol/sign?lang=en-us"
                method: POST
                cookies: tương ứng cookie
                headers={
                    **header chung,
                   "content-type": "application/json;charset=UTF-8",
                    **ORIGIN['act_hoyolab'],
                    'x-rpc-app_version': '',
                    'x-rpc-device_id': cookies["_HYVUUID"],
                    'x-rpc-device_name': '',
                    'x-rpc-lrsag': '',
                    'x-rpc-platform': '4',
                },
                 json_data={
                'act_id': cls.ACT_ID
            }
                => response là {'retcode':..., 'message':..., 'data':...}
                Tới đoạn này thì return account: {retcode:..., message:..., data:...} vì thành công hay thất bại thì đây cũng là điểm cuối của công việc điểm danh, lưu lại thông tin này và thoát hàm điểm danh gemshin.
        
        Star Rail: - Luồng 2 - Logic tương tự Genshin nhưng API có khác chút:
            API - is_sign:
                url: "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/info"
                method: GET
                cookies: tương ứng cookie
                headers={
                    **header chung,
                    **ORIGIN['act_hoyolab'],
                    'x-rpc-signgame': 'hkrpg',
                },
                params={
                    'lang': 'en-us',
                    'act_id': ACT_ID tương ứng game (TH này của Star Rail)
                }
                => response là {'retcode':..., 'message':..., 'data':...}
            
            API - sign (submit sign):
                url: "https://sg-public-api.hoyolab.com/event/luna/hkrpg/os/sign"
                method: POST
                cookies: tương ứng cookie
                headers={
                    **header chung,
                    **ORIGIN['act_hoyolab'],
                    'x-rpc-client_type': '5',
                    'x-rpc-platform': '4',
                    'x-rpc-signgame': 'hkrpg',
                },
                json_data={
                    'act_id': cls.ACT_ID,
                    'lang': 'en-us',
                }   
                => response là {'retcode':..., 'message':..., 'data':...}
        
        Zzz: - Luồng 3 - Logic tương tự Genshin nhưng API có khác chút:
            API - is_sign:
                url: "https://sg-public-api.hoyolab.com/event/luna/zzz/os/info"
                method: GET
                cookies: tương ứng cookie
                headers={
                    **header chung,
                    **ORIGIN['act_hoyolab'],
                    'x-rpc-signgame': 'zzz',
                },
                params={
                    'lang': 'en-us',
                    'act_id': ACT_ID tương ứng game (TH này của Zzz)
                }
                => response là {'retcode':..., 'message':..., 'data':...}
            
            API - sign (submit sign):
                url: "https://sg-public-api.hoyolab.com/event/luna/zzz/os/sign"
                method: POST
                cookies: tương ứng cookie
                headers={
                    **header chung,
                    **ORIGIN['act_hoyolab'],
                    'x-rpc-client_type': '5',
                    'x-rpc-platform': '4',
                    'x-rpc-signgame': 'zzz',
                },
                json_data={
                    'act_id': cls.ACT_ID,
                    'lang': 'en-us',
                }   
                => response là {'retcode':..., 'message':..., 'data':...}
    
    - Công việc check Redeem:
        Ta sẽ làm hai công việc song song:
            1. Fetch cdkeys (luồng 1)
            2. Fetch uid của player (luồng 2)
            Tại vì nếu có cdkey mà không có uid thì không thể redeem được. Còn có uid nhưng cdkeys trống thì cũng không thể redeem được. Cả uid và cdkey đều phải có thì mới redeem được. Vì vậy một trong 2 diều kiện mà không có thì in ra màn hình và thoát hàm (hàm này cũng là kết thúc của công việc check redeem).
        
        - Công việc 1: Fetch cdkeys
            - Call api fetch cdkeys (cdkeys chính là code hay redeem code mà nhà phát hành tặng):
            3 luồng:
                luồng 1: call api fetch cdkeys - genshin
                luồng 2: call api fetch cdkeys - star rail
                luồng 3: call api fetch cdkeys - zzz
            
            nếu sau 3 luồng không thu thâp được cdkey nào thì thông báo ra màn hình và thoát hàm (hàm này cũng là kết thúc của công việc check redeem)

            Nếu sau 3 luồng thu thâp được cdkey (cdkey >= 1) thì:
                xác định game nào có key.
                ví dụ:
                    sau khi duyệt qua 3 game:
                        TH1: chỉ có 1 game genshin => genshin: list key
                        TH2: có 2 game genshin và star rail => genshin: list key, star rail: list key
                        TH3: có 3 game genshin, star rail và zzz => genshin: list key, star rail: list key, zzz: list key
                        TH4: có 2 game star rail và zzz => star rail: list key, zzz: one key
                        TH5: có 2 game genshin và zzz => genshin: list key, zzz: one key
                        TH6: có 1 game star rail => star rail: list key
                        TH7: có 1 game zzz => zzz: one key
                        TH8: không có game nào có code => thông báo ra màn hình và thoát hàm (hàm này cũng là kết thúc của công việc check redeem)

            API:
                url: "https://bbs-api-os.hoyolab.com/community/painter/wapi/circle/channel/guide/material"
                method: GET
                cookies: tương ứng cookie
                headers={
                    **header chung,
                    **ORIGIN['act_hoyolab'],
                    'x-rpc-client_type': '4',
                    'x-rpc-device_id': cookies['_MHYUUID'],
                    'x-rpc-hour': current_hour(),
                    'x-rpc-language': 'en-us',
                    'x-rpc-lrsag': '',
                    'x-rpc-page_info': '{"pageName":"","pageType":"","pageId":"","pageArrangement":"","gameId":""}',
                    'x-rpc-page_name': '',
                    'x-rpc-show-translated': 'false',
                    'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                    'x-rpc-sys_version': 'Windows NT 10.0',
                    'x-rpc-timezone': 'Asia/Bangkok',
                    'x-rpc-weekday': rpc_weekday(),
                },
                params={
                    'game_id': PARAMS[game_choice]['game_id'],  //chính là id của game tương ứng
                }
                => response là {'retcode':..., 'message':..., 'data':...}

                Nếu "retcode" != 0 nghĩa là  request đã bị lỗi. continue tiếp sang game khác. Nếu sau khi duyệt qua 3 game mà không thu thâp được cdkey nào thì thông báo ra màn hình và thoát hàm (hàm này cũng là kết thúc của công việc check redeem)

                Nếu "retcode" == 0 nghĩa là request đã thành công. tiếp tục xử lý dò trong response như code bên dưới (cdkey trong api này được gọi là exchange_code):
                    return [
                        bonus['exchange_code']
                        for module in r.get('data', {}).get('modules', [])
                        if (group := module.get('exchange_group'))
                        for bonus in group.get('bonuses', [])
                        if bonus.get('exchange_code')
                    ]
            
        - Công việc 2: Fetch uid của player
            Duyệt qua 3 game genshin, star rail, zzz, mỗi game duyệt qua 4 region (asia, usa, euro, tw) để lấy ra tất cả uid của player trong 3 game. Vì api này là get và không bị hạn chế gì nên 1 account sẽ chạy song song 12 luồng (3 game * 4 region) để lấy ra uid.

            Ví dụ:
                Có 1 account: duyệt qua 3 game * 4 region => 12 luồng
                Có 2 account: duyệt ... => 2 * 12 = 24 luồng
                Có 4 account: duyệt ... => 4 *12 = 48 luồng
                    Nếu player tạo account thì game - server đó sẽ generate ra uid lúc, đó call api sẽ trả ra được. còn player không chơi thì uid khi call request sẽ không có.

                    Vì vậy trong 4 account này nếu chỉ chơi mỗi asia thì mỗi game sẽ có 1 uid ở server aisa, nếu trong 3 game có genhsin chơi server asia và usa, star rail chỉ asia, zzz chưa chơi thì kết quả là: 
                      Genshin: uid_asia, uid_usa
                      Star Rail: uid_asia
                      ZZZ: không có uid -> bỏ qua, chỉ lưu lại game:uid nếu có uid
                      Final result: 
                        genshin: [uid_asia, uid_usa]
                        star rail: [uid_asia]
                        zzz: []
            
            
            API getUserGameRolesByLtoken:
                url: "https://api-account-os.hoyolab.com/binding/api/getUserGameRolesByLtoken"
                cookies: tương ứng cookie (tất cả api trong file này đều kèm cookie, nếu không có thì sẽ lỗi 40x)
                method: GET
                headers: {
                    **HEADER chung,
                    **ORIGIN['hoyolab'],
                    'x-rpc-client_type': '4',
                    'x-rpc-device_id': cookies['_MHYUUID'],
                    'x-rpc-hour': current_hour(),   // phải viết hàm current_hour() để lấy giờ hiện tại
                    'x-rpc-language': 'en-us',
                    'x-rpc-lrsag': '',
                    'x-rpc-page_name': 'HomeGamePage',
                    'x-rpc-show-translated': 'false',
                    'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                    'x-rpc-sys_version': 'Windows NT 10.0',
                    'x-rpc-timezone': 'Asia/Bangkok',
                    'x-rpc-weekday': rpc_weekday(),  // phải viết hàm rpc_weekday() để lấy thứ trong tuần   
                }
                params={
                    'region': PARAMS[game_choice]['region'][region_choice],
                    'game_biz': PARAMS[game_choice]['game_biz']
                }
                => response là {'retcode':..., 'message':..., 'data':...}

                TH: response trả về "retcode" != 0 nghĩa là xảy ra lỗi. => nghĩa là không lấy được uid của game/server tương ứng. các luồng khác vẫn chạy bình thường. mục đích của việc duyệt qua 3 game * 4 region là để lấy ra tất cả uid của player trong 3 game. Nếu gặp lỗi hoặc không tìm thấy uid thì cứ tiếp tục chạy cho đến hết. nếu đến cuối cùng account/cookie đó duyệt qua 3 game - 4 server mà không có một cái uid nào => không lưu kết quả của account này. (Nghĩa là tài khoản này có tạo trên hoyolab nhưng chưa vào game lần nào. Muốn generate uid thì phải vào game lần đầu tiên, trường hợp này thì bỏ qua vì chỉ tài khoản hoyolab thì không thực hiện gọi API redeem code từng game/server được)

                TH: response trả về "retcode" == 0 nghĩa là request thành công, tiếp tục xử lý dò trong response như code bên dưới:
                    uid = r['data']['list'][0].get('game_uid')
                    - nghĩa là "data" chứa một [] nhưng chỉ có 1 phần tử (index 0) là "game_uid", cái này là uid của player trong game tương ứng với region tương ứng.
                
                ví dụ:
                acc_1: {
                    genshin: [uid_asia, uid_usa],
                    star rail: [uid_asia],
                    zzz: []
                }
                acc_2: {
                    genshin: [],
                    star rail: [uid_asia],
                    zzz: [uid_asia]
                }
                acc_3: {
                    genshin: [],
                    star rail: [],
                    zzz: []
                } -> acc_3 sẽ không được lưu lại vì không có uid nào. Nghĩa là giá trị thực tế chỉ lưu acc_1 và acc_2
                acc_4: {
                    only genshin: [uid_america]
                } -> lúc này cache sẽ lưu acc_1, acc_2, acc_4

        
        API exchange_cdkey - Nhập code vào account (game, server tương ứng)
            Genshin:
                url: "https://public-operation-hk4e.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl"
                method: GET
                cookie:  tương ứng từng account
                headers: {
                    **HEADER chung,
                    **ORIGIN['hoyolab'],
                    'x-rpc-client_type': '4',
                    'x-rpc-device_id': cookies['_MHYUUID'], // lấy từ cookie
                    'x-rpc-hour': current_hour(), // phải viết hàm current_hour() để lấy giờ hiện tại
                    'x-rpc-language': 'en-us',
                    'x-rpc-lrsag': '',
                    'x-rpc-page_name': 'HomeGamePage',
                    'x-rpc-show-translated': 'false',
                    'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                    'x-rpc-sys_version': 'Windows NT 10.0',
                    'x-rpc-timezone': 'Asia/Bangkok',
                    'x-rpc-weekday': rpc_weekday(), // phải viết hàm rpc_weekday() để lấy thứ trong tuần
                }
                params={
                    'cdkey': cdkey,
                    'game_biz': GAME_BIZ tương ứng,
                    'lang': 'en',
                    'region': PARAMS['gs']['region'][region_choice] - tương ứng với game/server (region là server),
                    't': unix_ms(), // phải viết hàm unix_ms() để lấy thời gian hiện tại dạng ms
                    'uid': uid
                }

                => lưu lại repsons tương ứng account, game, server, cdkey. Không quan tâm đến thành công hay thất bại vì hàm này là hàm nhập code, nếu thành công thì sẽ có response trả về, nếu thất bại thì cũng có response trả về. Mục đích là để lưu lại response tương ứng account, game, server, cdkey. từ đó dễ làm báo cáo in ra màn hình cho tôi xem trực quan.

            Star Rail:
                url: "https://public-operation-hkrpg.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl"
                method: GET
                cookie:  tương ứng từng account
                headers: {
                    **HEADER chung,
                    **ORIGIN['hoyolab'],
                    'x-rpc-client_type': '4',
                    'x-rpc-device_id': cookies['_MHYUUID'],
                    'x-rpc-hour': current_hour(),
                    'x-rpc-language': 'en-us',
                    'x-rpc-lrsag': '',
                    'x-rpc-page_name': 'HomeGamePage',
                    'x-rpc-show-translated': 'false',
                    'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                    'x-rpc-sys_version': 'Windows NT 10.0',
                    'x-rpc-timezone': 'Asia/Bangkok',
                    'x-rpc-weekday': rpc_weekday(),
                }
                params={
                    'cdkey': cdkey,
                    'game_biz': GAME_BIZ tương ứng,
                    'lang': 'en',
                    'region': PARAMS['sr']['region'][region_choice] - tương ứng với game/server (region là server),
                    't': unix_ms(), // phải viết hàm unix_ms() để lấy thời gian hiện tại dạng ms
                    'uid': uid
                }

                => lưu lại repsons tương ứng account, game, server, cdkey. Không quan tâm đến thành công hay thất bại vì hàm này là hàm nhập code, nếu thành công thì sẽ có response trả về, nếu thất bại thì cũng có response trả về. Mục đích là để lưu lại response tương ứng account, game, server, cdkey. từ đó dễ làm báo cáo in ra màn hình cho tôi xem trực quan.
            ZZZ:
                url: "https://public-operation-nap.hoyolab.com/common/apicdkey/api/webExchangeCdkeyHyl"
                method: GET
                cookie:  tương ứng từng account
                headers: {
                    **HEADER chung,
                    **ORIGIN['hoyolab'],
                    'x-rpc-client_type': '4',
                    'x-rpc-device_id': cookies['_MHYUUID'],
                    'x-rpc-hour': current_hour(),
                    'x-rpc-language': 'en-us',
                    'x-rpc-lrsag': '',
                    'x-rpc-page_name': 'HomeGamePage',
                    'x-rpc-show-translated': 'false',
                    'x-rpc-source_info': '{"sourceName":"","sourceType":"","sourceId":"","sourceArrangement":"","sourceGameId":""}',
                    'x-rpc-sys_version': 'Windows NT 10.0',
                    'x-rpc-timezone': 'Asia/Bangkok',
                    'x-rpc-weekday': rpc_weekday(),
                }
                params={    
                    'cdkey': cdkey,
                    'game_biz': GAME_BIZ tương ứng,
                    'lang': 'en',
                    'region': PARAMS['zzz']['region'][region_choice] - tương ứng với game/server (region là server),
                    't': unix_ms(), // phải viết hàm unix_ms() để lấy thời gian hiện tại dạng ms
                    'uid': uid
                }

                => lưu lại repsons tương ứng account, game, server, cdkey. Không quan tâm đến thành công hay thất bại vì hàm này là hàm nhập code, nếu thành công thì sẽ có response trả về, nếu thất bại thì cũng có response trả về. Mục đích là để lưu lại response tương ứng account, game, server, cdkey. từ đó dễ làm báo cáo in ra màn hình cho tôi xem trực quan.
                
## Khi trên git action tự động chạy, tôi muốn in ra màn hình cho tôi xem trực quan, có thể tham khảo format kiểu như dưới:


--- CHECK-IN --- // Đa luồng 1
=== acc_1 ===   (giả sử acc_1 có chơi cả 3 game)    // Đa luồng 1.1
genshin: kết quả (nếu thất bại thì in ra message thất bại đó để tôi đi tìm nguyên nhân thất bại dễ dàng fix hơn)
star_rail: kết quả
zzz: kết quả
=== acc_2 ===   (giả sử acc_2 không có chơi star_rail) // Đa luồng 1.2
genshin: kết quả
zzz: kết quả


--- REDEEM CODE --- // Đa luồng 2
=== acc_1 ===   // Đa luồng 2.1
genshin:
    server_1:   // đa luồng 2.1.1
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
    server_2:   // đa luồng 2.1.2
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
star_rail:
    server_1:   // đa luồng 2.1.3
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
    server_2:   // đa luồng 2.1.4
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
    server_3:   // đa luồng 2.1.5
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
zzz:    // game zzz thường nhà phát hành chỉ có 1 code ; //giả định acc_1 này zzz chơi 2 server
    server_1 (asia):   // đa luồng 2.1.6
        code_1: kết quả
        -> đã nhập xong 1 code duy nhất, lưu kết quả vào cache
    server_2 (america):   // đa luồng 2.1.7
        code_1: kết quả
        -> đã nhập xong 1 code duy nhất, lưu kết quả vào cache
=== acc_2 ===   // Đa luồng 2.2
genshin:
    server_1:   // đa luồng 2.2.1
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
    server_2:   // đa luồng 2.2.2
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
    server_3:   // đa luồng 2.2.3
        code_1: kết quả
        delay 5s
        code_2: kết quả
        delay 5s
        code_3: kết quả
        -> đã nhập xong 3 code, lưu kết quả vào cache
zzz:
    server_1 (asia):   // đa luồng 2.2.4
        code_1: kết quả
        -> đã nhập xong 1 code duy nhất, lưu kết quả vào cache
    server_2 (america):   // đa luồng 2.2.5
        code_1: kết quả
        -> đã nhập xong 1 code duy nhất, lưu kết quả vào cache
--- END ---