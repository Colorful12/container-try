import { Component, OnInit } from '@angular/core';
import { ApiService } from './api.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class AppComponent implements OnInit {
  healthStatus = '';

  constructor(private apiService: ApiService) { }

  ngOnInit() {
    this.apiService.getHealth().subscribe({
      next: (res) => this.healthStatus = res.status,
      error: (err) => this.healthStatus = 'Error: ' + err.message
    });
  }
}
