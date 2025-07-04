import requests
import json
import time

start_time = time.time()

text = 'hello,world'
speaker_id = 1 # zunda

# create audio querry
base_url = 'http://127.0.0.1:50021'

query_response = requests.post(
	f'{base_url}/audio_query',
	params = {'speaker': speaker_id,
			  'text' : text}
)

if query_response.status_code != 200:
	print('audio query request failed:',query_response.status_code,query_response.text)
	
# synthesis request
synthesis_response = requests.post(
	f'{base_url}/synthesis',
	params = {'speaker' : speaker_id},
	headers = {'Content-Type' : 'application/json'},
	data = query_response.content
)

if synthesis_response.status_code == 200:
	# save voice
	with open(f'voices/output.wav','wb') as f:
		f.write(synthesis_response.content)
	print('save voice file commplete!: voices/output.wav')
else:
	print('synthesis request failed:',synthesis_response.status_code, synthesis_response.text)

end_time = time.time() - start_time
print(f'time:{end_time:.2f} sec')
