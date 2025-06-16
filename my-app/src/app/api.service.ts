import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
    providedIn: 'root', // サービスの提供場所をルート（アプリ全体）に設定
})
export class ApiService {
    constructor(private http: HttpClient) { }

    getHealth(): Observable<{ status: string }> {
        return this.http.get<{ status: string }>('http://localhost:8000/health');
    }
}
