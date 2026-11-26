import { Routes } from '@angular/router';
import { Home } from './home/home';
import { ProfilePage } from './profile/profile-page';

export const routes: Routes = [
  { path: '', component: Home },
  { path: 'profile', component: ProfilePage },
  { path: '**', redirectTo: '' },
];
