import os

def play_sound(sound_path):
    os.system(f'aplay {sound_path}')
    # os.system(f'aplay -D plughw:1,0 "{sound_path}"') 再生されないのはHDMI側に音声を投げている可能性があるため

SCR_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(SCR_DIR,"test_sound.wav")

play_sound(FILE_PATH)