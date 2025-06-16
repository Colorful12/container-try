import { Component, OnInit, inject } from '@angular/core';
import { ApiService } from './api.service';
import { HttpClientModule } from '@angular/common/http';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [HttpClientModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class AppComponent implements OnInit {
  healthStatus = '';
  private apiService = inject(ApiService);

  ngOnInit() {
    this.apiService.getHealth().subscribe({
      next: (res) => this.healthStatus = res.status,
      error: (err) => this.healthStatus = 'Error: ' + err.message
    });
  }
}
