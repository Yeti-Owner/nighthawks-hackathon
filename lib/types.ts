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
