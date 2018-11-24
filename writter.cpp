#include <Arduino.h>
int digitalPinStates[14];

void setup() {
	init();
	Serial.begin(9600);
	for (int i = 2; i < 14; i++) {
		pinMode(i, INPUT);
		digitalWrite(i, HIGH);
	}
}

int main() {
	setup();
	while (true) {
		for (int i = 2; i < 14; i++) {
			int pinValNow = digitalRead(i);
			if (pinValNow != digitalPinStates[i]) {
				digitalPinStates[i] = pinValNow;
				Serial.print(i);
				Serial.print(":");
				Serial.println(digitalPinStates[i]);
			}
		}
	}
	return 0;
}
