import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidationErrors,
  ValidatorFn,
} from '@angular/forms';
import { ChatMessage, Experience, UserProfile } from '../core/api.types';
import { ProfileService } from './profile.service';

/** Core fields a plan needs; mirrors CORE_FIELDS in backend/app/profile.py. */
const CORE_FIELDS = [
  'height_cm',
  'weight_kg',
  'experience',
  'goals',
  'workout_days',
  'session_minutes',
] as const;

const FIELD_LABELS: Record<(typeof CORE_FIELDS)[number], string> = {
  height_cm: 'height',
  weight_kg: 'weight',
  experience: 'experience',
  goals: 'goals',
  workout_days: 'workout days',
  session_minutes: 'session length',
};

/** Same limits as backend/app/guardrails.py (DESIGN.md section 8). */
export const MAX_MESSAGE_LENGTH = 2000;
export const MAX_CHAT_MESSAGES = 40;

/** A chat message as shown on the page; refused ones are not sent again. */
interface ShownMessage extends ChatMessage {
  refused: boolean;
}

/**
 * The chat to send: refused exchanges left out, and only the newest
 * MAX_CHAT_MESSAGES kept. Earlier details are already in the saved profile,
 * which the back end sends to the model as well.
 */
function historyToSend(shown: ShownMessage[]): ChatMessage[] {
  return shown
    .filter((message) => !message.refused)
    .slice(-MAX_CHAT_MESSAGES)
    .map(({ role, content }) => ({ role, content }));
}

/** Empty, or a number strictly between min and max (Pydantic gt / lt). */
function between(min: number, max: number): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = control.value as number | null;
    if (value === null) return null;
    return value > min && value < max ? null : { range: true };
  };
}

/** Empty, or a whole number from min to max (Pydantic ge / le). */
function wholeFrom(min: number, max: number): ValidatorFn {
  return (control: AbstractControl): ValidationErrors | null => {
    const value = control.value as number | null;
    if (value === null) return null;
    return Number.isInteger(value) && value >= min && value <= max ? null : { range: true };
  };
}

function text() {
  return new FormControl('', { nonNullable: true });
}

/** Editable copy of UserProfile; list fields are comma-separated text. */
function profileForm() {
  return new FormGroup({
    name: text(),
    height_cm: new FormControl<number | null>(null, between(100, 250)),
    weight_kg: new FormControl<number | null>(null, between(30, 300)),
    experience: new FormControl<Experience | ''>('', { nonNullable: true }),
    goals: text(),
    workout_days: new FormControl<number | null>(null, wholeFrom(1, 6)),
    session_minutes: new FormControl<number | null>(null, wholeFrom(15, 120)),
    split_preference: text(),
    equipment: text(),
    injuries: text(),
    health_notes: text(),
    dietary_preferences: text(),
    dietary_restrictions: text(),
  });
}

type ProfileForm = ReturnType<typeof profileForm>;
type ProfileFormValue = ReturnType<ProfileForm['getRawValue']>;

function toForm(profile: UserProfile): ProfileFormValue {
  return {
    name: profile.name ?? '',
    height_cm: profile.height_cm,
    weight_kg: profile.weight_kg,
    experience: profile.experience ?? '',
    goals: profile.goals.join(', '),
    workout_days: profile.workout_days,
    session_minutes: profile.session_minutes,
    split_preference: profile.split_preference ?? '',
    equipment: profile.equipment.join(', '),
    injuries: profile.injuries.join(', '),
    health_notes: profile.health_notes ?? '',
    dietary_preferences: profile.dietary_preferences.join(', '),
    dietary_restrictions: profile.dietary_restrictions.join(', '),
  };
}

function orNull(value: string): string | null {
  return value.trim() || null;
}

function toList(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter((item) => item !== '');
}

function fromForm(value: ProfileFormValue): UserProfile {
  return {
    name: orNull(value.name),
    height_cm: value.height_cm,
    weight_kg: value.weight_kg,
    experience: value.experience || null,
    goals: toList(value.goals),
    workout_days: value.workout_days,
    session_minutes: value.session_minutes,
    split_preference: orNull(value.split_preference),
    equipment: toList(value.equipment),
    injuries: toList(value.injuries),
    health_notes: orNull(value.health_notes),
    dietary_preferences: toList(value.dietary_preferences),
    dietary_restrictions: toList(value.dietary_restrictions),
  };
}

/** Readable message for a failed request; never repeats what the user typed. */
function errorText(err: unknown): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) return "Can't reach the back end. Is it running on port 8000?";
    if (err.status === 502) return 'The assistant is unavailable right now. Please try again later.';
    const body = err.error as { error?: unknown; detail?: unknown } | null;
    if (body && typeof body.error === 'string') {
      return typeof body.detail === 'string' ? `${body.error}: ${body.detail}` : body.error;
    }
  }
  return 'Something went wrong. Please try again.';
}

/** Profile page: chat to build the profile, then check and edit it (Step A3). */
@Component({
  selector: 'app-profile-page',
  imports: [ReactiveFormsModule],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.css',
})
export class ProfilePage {
  private readonly profiles = inject(ProfileService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly maxLength = MAX_MESSAGE_LENGTH;

  // Chat panel. The history lives only on this page; the profile is saved.
  // Refused exchanges stay on screen but are not sent again (Step C3).
  protected readonly messages = signal<ShownMessage[]>([]);
  protected readonly sending = signal(false);
  protected readonly chatNotice = signal('');
  protected readonly chatError = signal('');
  protected readonly chatForm = new FormGroup({ message: text() });

  // Profile card.
  protected readonly form = profileForm();
  protected readonly loading = signal(true);
  protected readonly loadError = signal('');
  protected readonly saving = signal(false);
  protected readonly saveMessage = signal('');
  protected readonly saveError = signal('');

  /** Changes whenever the card changes, so the values below recompute. */
  private readonly formChanged = toSignal(this.form.valueChanges);

  /** Core fields still empty in the card, as readable labels. */
  protected readonly missing = computed(() => {
    this.formChanged();
    const profile = fromForm(this.form.getRawValue());
    return CORE_FIELDS.filter((field) => {
      const value = profile[field];
      return Array.isArray(value) ? value.length === 0 : value === null;
    }).map((field) => FIELD_LABELS[field]);
  });

  /**
   * True when the card has edits that are not saved. A chat reply replaces the
   * card with the saved profile plus the chat's changes, so chatting waits.
   */
  protected readonly unsavedEdits = computed(() => {
    this.formChanged();
    return this.form.dirty;
  });

  /** Chat and save each change the saved profile, so only one runs at a time. */
  protected readonly canSend = computed(
    () => !this.sending() && !this.saving() && !this.loading() && !this.unsavedEdits(),
  );
  protected readonly canSave = computed(
    () => !this.saving() && !this.sending() && !this.loading() && !this.loadError(),
  );

  constructor() {
    // Old save results no longer apply once the card changes.
    this.form.valueChanges.pipe(takeUntilDestroyed()).subscribe(() => {
      this.saveMessage.set('');
      this.saveError.set('');
    });

    this.profiles
      .getProfile()
      .pipe(takeUntilDestroyed())
      .subscribe({
        next: (profile) => {
          this.showProfile(profile);
          this.loading.set(false);
        },
        error: (err: unknown) => {
          this.loadError.set(`Couldn't load your saved profile. ${errorText(err)}`);
          this.loading.set(false);
        },
      });
  }

  protected send(): void {
    const content = this.chatForm.controls.message.value.trim();
    if (!content || !this.canSend()) return;
    this.chatNotice.set('');
    this.chatError.set('');
    if (content.length > MAX_MESSAGE_LENGTH) {
      this.chatError.set('Messages can be at most 2,000 characters.');
      return;
    }
    const before = this.messages();
    const question: ShownMessage = { role: 'user', content, refused: false };
    this.messages.set([...before, question]);
    this.chatForm.reset();
    this.sending.set(true);
    this.profiles
      .chat(historyToSend([...before, question]))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response) => {
          const refused = response.refused;
          this.messages.set([
            ...before,
            { ...question, refused },
            { role: 'assistant', content: response.reply, refused },
          ]);
          if (refused) {
            this.chatNotice.set("The assistant couldn't help with that message.");
          }
          this.showProfile(response.profile);
          this.sending.set(false);
        },
        error: (err: unknown) => {
          // Take the message back out so a retry does not send it twice.
          this.messages.set(before);
          this.chatForm.setValue({ message: content });
          this.chatError.set(errorText(err));
          this.sending.set(false);
        },
      });
  }

  protected save(): void {
    if (!this.canSave()) return;
    this.saveMessage.set('');
    this.saveError.set('');
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.saveError.set('Please fix the highlighted fields first.');
      return;
    }
    this.saving.set(true);
    this.profiles
      .saveProfile(fromForm(this.form.getRawValue()))
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (saved) => {
          this.showProfile(saved);
          this.saveMessage.set('Saved.');
          this.saving.set(false);
        },
        error: (err: unknown) => {
          this.saveError.set(errorText(err));
          this.saving.set(false);
        },
      });
  }

  /** True when a field has a value outside its allowed range. */
  protected showRangeError(field: keyof ProfileFormValue): boolean {
    const control = this.form.controls[field];
    return control.invalid && control.touched;
  }

  /** Puts a saved profile in the card; pristine first so `unsavedEdits` is false. */
  private showProfile(profile: UserProfile): void {
    this.form.markAsPristine();
    this.form.markAsUntouched();
    this.form.setValue(toForm(profile));
  }
}
