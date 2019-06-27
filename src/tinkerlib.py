import machine
import time

# TODO
#  - servo
#  - soil moisture sensor
#  - OLED display
#  - mikrofon
#  - partikel-sensor
#  - pulsmåler


class LED:
    def __init__(self, pin):
        self.pin = pin
        # Mode function not available on ESP boards
        # self.pin.mode(machine.Pin.OUT)

    def on(self):
        self.pin.value(1)

    def off(self):
        self.pin.value(0)

class Potentiometer():
    """ ESP32: ports 32-39, ESP8266: ADC(0)"""
    def __init__(self, pin):
        self.pin = pin
        self.adc = machine.ADC(self.pin)
        self.adc.width(machine.ADC.WIDTH_10BIT)
        self.adc.atten(machine.ADC.ATTN_11DB)

    def read(self):
        return self.adc.read()

class DustSensor():
    """ """
    def __init__(self, pin, sampletime_ms=30000):
        self.pin = pin
        self.sampletime_ms = sampletime_ms

    # Waits for the pin to turn LOW/HIGH, depending on the value argument
    # and measures how long time it has that value.
    def _pulseInTimeout(self, pin, value, endTime):
        # Wait till we hit the wanted value
        while pin.value() != value:
            if(time.ticks_ms() > endTime):
                return 0
        # Start timing
        start = time.ticks_us()
        # Wait till we are no longer == value (or time passes)
        while pin.value() == value and time.ticks_ms() < endTime:
            pass
        now = time.ticks_us()
        tdiff = time.ticks_diff(now, start)
        return tdiff

    def read(self):
        starttime_ms = time.ticks_ms()
        endTime = starttime_ms + self.sampletime_ms
        lowpulseoccupancy_us = 0
        while time.ticks_ms() < endTime:
            duration_us = self._pulseInTimeout(self.pin, 0, endTime)
            lowpulseoccupancy_us = lowpulseoccupancy_us+duration_us
        # Integer percentage 0%-100%
        ratio = lowpulseoccupancy_us/(self.sampletime_ms*10.0)
        # Using spec sheet curve
        concentration = 1.1*pow(ratio, 3)-3.8*pow(ratio, 2)+520*ratio+0.62
        return concentration

class PIRSensor():
    """Passive InfraRed (PIR) sensor - detects motion"""
    def __init__(self, pin, callback):
        self.pin = pin
        self.callback = callback
        self.pin.irq(handler=self.on_rising,
                     trigger=machine.Pin.IRQ_RISING)

    def on_rising(self, pin):
        irq_state = machine.disable_irq()
        self.callback()
        machine.enable_irq(irq_state)

    def value(self):
        return self.pin.value()

class Button():
    """TinkerKit Crash Sensor / button"""
    def __init__(self, pin, button_down, button_up=None):
        self.pin = pin
        self.pin.init(pull=machine.Pin.PULL_UP)
        self.button_down = button_down
        self.button_up = button_up
        self.state = self.pin.value()
        self.pin.irq(handler=self.on_change,
                     trigger=machine.Pin.IRQ_RISING | machine.Pin.IRQ_FALLING)

    def on_change(self, pin):
        irq_state = machine.disable_irq()
        new_state = pin.value()
        if self.state == 0 and new_state == 1:
            if self.button_up:
                self.button_up()
        elif self.state == 1 and new_state == 0:
            self.button_down()
        self.state = new_state
        machine.enable_irq(irq_state)

class ADKeypad():
    """5 button keypad"""
    def __init__(self, pin, button_down=None, button_up=None, timer=3):
        self.pin = pin
        self.adc = machine.ADC(self.pin)
        self.adc.width(machine.ADC.WIDTH_10BIT)
        self.adc.atten(machine.ADC.ATTN_11DB)
        self.button_down = button_down
        self.button_up = button_up
        self.button_last_state = self.button_state()
        self.tim = machine.Timer(timer)
        self.tim.init(period=20,
                      mode=machine.Timer.PERIODIC,
                      callback=self.button_check)

    def voltage_to_key(self, v):
        thresholds = [10, 20, 70, 150, 600]
        for i in range(len(thresholds)):
            if v < thresholds[i]:
                return i
        return None

    def button_state(self):
        return self.voltage_to_key(self.adc.read())

    def button_check(self, t):
        new_state = self.button_state()
        if self.button_last_state != new_state:
            if new_state is None:
                if self.button_up:
                    self.button_up()
            else:
                if self.button_down:
                    self.button_down(new_state)
        self.button_last_state = new_state

class Buzzer:
    def __init__(self, pin):
        self.pin = pin
        self.pwm = machine.PWM(self.pin)

    def tone(self, frequency, duration=None, dutycycle=50):
        if frequency != 0:
            self.pwm.init()
            self.pwm.freq(frequency)
            self.pwm.duty(int(1023*dutycycle/100))
        if duration != None:
            time.sleep_ms(duration)
            self.pwm.deinit()

    def noTone(self):
        self.pwm.deinit()
