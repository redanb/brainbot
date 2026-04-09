import json; log = open('C:\\Users\\admin\\.antigravity\\master\\evolution_log.json', 'r', encoding='utf-8').read(); open('tmp_log_last50.json', 'w').write(log[-5000:])
