export interface StudySession {
  date: string;
  subject: string;
  duration: number;
  interruptions: number;
  focusScore: number;
  notes: string;
}

export interface DistractionSource {
  name: string;
  value: number;
  color: string;
}

export interface TopApp {
  name: string;
  count: number;
}

export interface DailyHour {
  date: string;
  hours: number;
}

export interface PhonePickupEvent {
  time: string;
  minutesUnattended: number;
  durationSeconds: number;
}

export interface FaceAwayEvent {
  time: string;
  durationSeconds: number;
}
