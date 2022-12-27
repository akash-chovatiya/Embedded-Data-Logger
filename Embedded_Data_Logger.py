# Import all necessary libraries and modules
import RPi.GPIO as rpi
from Adafruit_LED_Backpack import SevenSegment
from time import sleep, time
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.led_matrix.device import max7219

SSD = SevenSegment.SevenSegment(address=0x70)
SSD.begin()
rpi.setmode(rpi.BCM)
my_spi_interface = spi(port=0, device=1, gpio=noop())
my_max7219 = max7219(my_spi_interface, cascaded=1, block_orientation=90, rotate=0)

# Define various pins/buttons and set pins/buttons as an input/output or set to LOW
echo_pin = 12
trig_pin = 16
up_button = 26
right_button = 19
down_button = 13
left_button = 25
buzzer_button = 18

rpi.setup(up_button, rpi.IN, pull_up_down=rpi.PUD_UP)
rpi.setup(down_button, rpi.IN, pull_up_down=rpi.PUD_UP)
rpi.setup(right_button, rpi.IN, pull_up_down=rpi.PUD_UP)
rpi.setup(left_button, rpi.IN, pull_up_down=rpi.PUD_UP)
rpi.setup(buzzer_button, rpi.OUT)
rpi.setup(echo_pin, rpi.IN, pull_up_down=rpi.PUD_UP)
rpi.setup(trig_pin, rpi.OUT)
rpi.output(trig_pin, rpi.LOW)


# Acquisition of range measurement data from the ultrasonic ranging module
def us_ranging(echo_pin, trig_pin):
    rpi.output(trig_pin, rpi.HIGH)
    sleep(0.00001)
    rpi.output(trig_pin, rpi.LOW)

    while rpi.input(echo_pin) == 0:
        start_time = time()
    while rpi.input(echo_pin) == 1:
        end_time = time()

    echo_pulse_time = end_time - start_time
    return echo_pulse_time


# Visualization of range measurement data on 7-segment display as a percentage
def show_7SD(echo_pulse_time, alpha):
    scaled_value = (echo_pulse_time * (100.0 / alpha))
    scaled_echo_pulse = round(scaled_value, 1)
    scaled_echo_pulse_leading_zero = str(scaled_echo_pulse).zfill(5)

    digit = 0
    for character in scaled_echo_pulse_leading_zero:
        if character != '.':
            SSD.set_digit(digit, character)
            SSD.set_decimal(2, True)
            digit += 1
    SSD.write_display()


# Visualization of range measurement data on matrix LED display (MLD)
def MLD_show(echo_pulse_time, alpha):
    MLD_height = int(round(7 * (echo_pulse_time / alpha)))
    return MLD_height


# Updating the delay time between two successive measurements
def update_rate(channel):
    global t
    if t > 8:
        t = 1
    else:
        t = t + 1
    print('Update Rate = ', t)


# Store up to 100 data points
def archive_option(echo_pulse_time, k):
    k += 1
    archive.append(echo_pulse_time)
    if len(archive) > 100:
        k = 100
        archive.pop(0)
    return archive, k


# Pause the program by pressing left_button
def pause(channel):
    global run
    run = 1


# Navigate through the archived values and show actual value on 7SD and last 8 data points on MLD
def navigate_archive():
    global count_press
    archive_height = []

    for i in range(0, 9):
        counter = len(archive) - 1 - i - count_press
        navigated_value = archive[counter]
        navigated_height = MLD_show(navigated_value, alpha)
        archive_height.append(navigated_height)
    count_press = count_press + 1

    show_7SD(archive[len(archive) - count_press - 1], alpha)
    SSD.clear()

    with canvas(my_max7219) as draw:
        for j in range(0, 9):
            draw.point([8 - j, 7 - archive_height[j]], fill="white")


# An automatic calibration routine
def calibrate(channel):
    global alpha
    calibration = 0
    mean_value = 0
    print('Calibration Started')

    while calibration < 10:
        rpi.output(buzzer_button, rpi.HIGH)
        echo_pulse_time = us_ranging(echo_pin, trig_pin)
        print('Calibration_Measurement',calibration+1,':',echo_pulse_time)
        sleep(0.5)
        calibration = calibration + 1
        mean_value = mean_value + echo_pulse_time

    print('Calibration Finished')
    alpha = mean_value / (calibration)
    print('Calibrated_alpha:',alpha)
    rpi.output(buzzer_button, rpi.LOW)


alpha = 0.0097937
bar_height = []
archive = []
t = 1
run = 0
count_press = 0
j = 0
k = 0

rpi.add_event_detect(up_button, rpi.FALLING, callback=update_rate, bouncetime=200)
rpi.add_event_detect(left_button, rpi.FALLING, callback=pause, bouncetime=200)
rpi.add_event_detect(down_button, rpi.FALLING, callback=calibrate, bouncetime=200)


def main():
    global alpha, t, run, archive, bar_height, count_press, j, k

    if rpi.input(left_button) == 1 and run == 0:
        echo_pulse_time = us_ranging(echo_pin, trig_pin)
        show_7SD(echo_pulse_time, alpha)
        MLD_height = MLD_show(echo_pulse_time, alpha)
        [archive, k] = archive_option(echo_pulse_time, k)

        if len(bar_height) < 8:
            bar_height.append(MLD_height)
            with canvas(my_max7219) as draw:
                for i in range(0, j + 1):
                    draw.point([7 - i, 7 - bar_height[j - i]], fill="white")
            sleep(1)

        else:
            bar_height.pop(0)
            bar_height.append(MLD_height)
            with canvas(my_max7219) as draw:
                for i in range(0, 8):
                    draw.point([i, 7 - bar_height[i]], fill="white")
            sleep(t)
        SSD.clear()
        j += 1
        print('Archive(Len-',k,'):', archive)

    if rpi.input(left_button) == 0 and run == 0:
        pass

    if rpi.input(down_button) == 0:
        pass

    if rpi.input(right_button) == 0 and run == 1:
        sleep(1)
        navigate_archive()

    if rpi.input(left_button) == 0 and run == 1:
        run = 0
        count_press = 0


Data_Logger = True
while Data_Logger:
    try:
        main()
    except KeyboardInterrupt:
        print()
        print('Program has been stopped by User')
        Data_Logger = False
