import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)
servo_pin = 9 # GPIO9が特殊用途だから動かない可能性がる -> GPIO 18,12,13,19辺りを試す
GPIO.setup(servo_pin,GPIO.OUT)
pwm = GPIO.PWM(servo_pin,50)
pwm.start(0)

def set_servo_angle(angle):
    duty = angle / 18 + 2
    pwm.ChangeDutyCycle(duty)
    sleep(0.5)

set_servo_angle(90)