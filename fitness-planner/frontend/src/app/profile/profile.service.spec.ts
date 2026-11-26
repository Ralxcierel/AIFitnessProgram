import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ChatMessage, ProfileChatResponse, UserProfile } from '../core/api.types';
import { ProfileService } from './profile.service';

const SAMPLE: UserProfile = {
  name: 'Sam Sample',
  height_cm: 180,
  weight_kg: 80,
  experience: 'beginner',
  goals: ['get stronger'],
  workout_days: 3,
  session_minutes: 45,
  split_preference: null,
  equipment: [],
  injuries: [],
  health_notes: null,
  dietary_preferences: [],
  dietary_restrictions: [],
};

describe('ProfileService', () => {
  let service: ProfileService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ProfileService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('posts the whole chat', () => {
    const messages: ChatMessage[] = [{ role: 'user', content: 'I am 180 cm' }];
    const reply: ProfileChatResponse = {
      reply: 'Thanks!',
      profile: SAMPLE,
      missing_fields: [],
      refused: false,
    };
    let result: ProfileChatResponse | undefined;

    service.chat(messages).subscribe((response) => (result = response));
    const request = http.expectOne('/api/profile/chat');
    request.flush(reply);

    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ messages });
    expect(result).toEqual(reply);
  });

  it('gets the saved profile', () => {
    let result: UserProfile | undefined;
    service.getProfile().subscribe((profile) => (result = profile));
    const request = http.expectOne('/api/profile');
    request.flush(SAMPLE);

    expect(request.request.method).toBe('GET');
    expect(result).toEqual(SAMPLE);
  });

  it('puts the profile to save it', () => {
    let result: UserProfile | undefined;
    service.saveProfile(SAMPLE).subscribe((profile) => (result = profile));
    const request = http.expectOne('/api/profile');
    request.flush(SAMPLE);

    expect(request.request.method).toBe('PUT');
    expect(request.request.body).toEqual(SAMPLE);
    expect(result).toEqual(SAMPLE);
  });
});
