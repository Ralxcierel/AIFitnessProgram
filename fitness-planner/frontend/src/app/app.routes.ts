import { Routes } from '@angular/router';
import { Home } from './home/home';
import { LogPage } from './log/log-page';
import { ProfilePage } from './profile/profile-page';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'profile', component: ProfilePage },
  { path: 'log', component: LogPage },
  { path: '**', redirectTo: '' },
];
