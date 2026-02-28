const int SENSOR_PIN  = 2;
const int SWITCH_PIN  = 3;

bool foilTouching      = false;
bool wasTouching       = false;
bool sessionActive     = false;
bool lastSwitchState   = false;
bool hasBeenPickedUp   = false;   // only count PUT DOWN after a real pickup

unsigned long separatedStartMillis = 0;
unsigned long totalSeparatedTime   = 0;
unsigned long sessionSeparatedTime = 0;
int separationCount = 0;

struct Session {
  unsigned long duration;
};

Session sessions[50];
int sessionCount = 0;

void setup() {
  pinMode(SENSOR_PIN, INPUT_PULLUP);
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  Serial.begin(9600);
  Serial.println("=== Phone Pickup Tracker ===");
  Serial.println("Flip switch ON to start session");
  Serial.println("Flip switch OFF to end and send data");
  Serial.println("----------------------------");
}

void loop() {
  bool switchOn = (digitalRead(SWITCH_PIN) == LOW);

  // --- Switch ON: start a new session ---
  if (switchOn && !lastSwitchState) {
    sessionActive        = true;
    hasBeenPickedUp      = false;
    separationCount      = 0;
    sessionCount         = 0;
    totalSeparatedTime   = 0;
    separatedStartMillis = 0;
    foilTouching         = (digitalRead(SENSOR_PIN) == LOW);
    wasTouching          = foilTouching;       // sync so first read is not a transition
    Serial.println(">> SESSION STARTED");
    Serial.println("----------------------------");
  }

  // --- Switch OFF: end session and dump CSV data ---
  if (!switchOn && lastSwitchState) {
    sessionActive = false;

    // If phone is still picked up when session ends, record that last stretch
    if (hasBeenPickedUp && !foilTouching && separatedStartMillis > 0) {
      sessionSeparatedTime  = millis() - separatedStartMillis;
      totalSeparatedTime   += sessionSeparatedTime;
      if (sessionCount < 50) {
        sessions[sessionCount].duration = sessionSeparatedTime;
        sessionCount++;
      }
    }

    Serial.println("\n====== SESSION END ======");
    Serial.print("TOTAL_PICKUPS,");
    Serial.println(separationCount);
    Serial.print("TOTAL_SECONDS,");
    Serial.println(totalSeparatedTime / 1000.0, 2);

    for (int i = 0; i < sessionCount; i++) {
      Serial.print("SESSION,");
      Serial.print(i + 1);
      Serial.print(",");
      Serial.println(sessions[i].duration / 1000.0, 2);
    }

    Serial.println("====== END DATA ======");
    Serial.println(">> SESSION ENDED");
    Serial.println("Flip switch ON to start a new session");
  }

  lastSwitchState = switchOn;

  if (!sessionActive) return;

  foilTouching = (digitalRead(SENSOR_PIN) == LOW);

  // --- Phone lifted off sensor ---
  if (!foilTouching && wasTouching) {
    separationCount++;
    hasBeenPickedUp      = true;
    separatedStartMillis = millis();
    Serial.print(">> PICKED UP #");
    Serial.println(separationCount);
  }

  // --- Phone placed back on sensor (only after a real pickup) ---
  if (foilTouching && !wasTouching && hasBeenPickedUp) {
    sessionSeparatedTime  = millis() - separatedStartMillis;
    totalSeparatedTime   += sessionSeparatedTime;

    if (sessionCount < 50) {
      sessions[sessionCount].duration = sessionSeparatedTime;
      sessionCount++;
    }

    Serial.println(">> PUT DOWN");
    Serial.print("   Held for:        ");
    printDuration(sessionSeparatedTime);
    Serial.print("   Total pickups:   ");
    Serial.println(separationCount);
    Serial.print("   Total time held: ");
    printDuration(totalSeparatedTime);
    Serial.println("----------------------------");
  }

  wasTouching = foilTouching;
  delay(50);
}

void printDuration(unsigned long ms) {
  unsigned long totalSec = ms / 1000;
  unsigned long h = totalSec / 3600;
  unsigned long m = (totalSec % 3600) / 60;
  unsigned long s = totalSec % 60;
  char buf[50];
  sprintf(buf, "%02luh %02lum %02lus (%lu sec)\n", h, m, s, totalSec);
  Serial.print(buf);
}
