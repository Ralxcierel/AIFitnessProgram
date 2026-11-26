import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  ChatMessage,
  ProfileChatRequest,
  ProfileChatResponse,
  UserProfile,
} from '../core/api.types';

/** Calls the profile endpoints (Steps A1 and A2). */
@Injectable({ providedIn: 'root' })
export class ProfileService {
  private readonly http = inject(HttpClient);

  /** Sends the whole chat so far; the last message must be from the user. */
  chat(messages: ChatMessage[]): Observable<ProfileChatResponse> {
    const body: ProfileChatRequest = { messages };
    return this.http.post<ProfileChatResponse>('/api/profile/chat', body);
  }

  /** The saved profile, or an empty one if nothing is saved yet. */
  getProfile(): Observable<UserProfile> {
    return this.http.get<UserProfile>('/api/profile');
  }

  /** Replaces the saved profile and returns what was saved. */
  saveProfile(profile: UserProfile): Observable<UserProfile> {
    return this.http.put<UserProfile>('/api/profile', profile);
  }
}
