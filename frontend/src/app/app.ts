import { Component, OnInit, OnDestroy, ViewChild, ElementRef, inject } from '@angular/core';
import { ApiService } from './api.service';
import { HttpClientModule } from '@angular/common/http';

interface Cat {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [HttpClientModule],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class AppComponent implements OnInit, OnDestroy {
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  healthStatus = '';
  cats: Cat[] = [];
  fps = 0;
  private apiService = inject(ApiService);
  private ws: WebSocket | null = null;
  private animationId: number | null = null;
  private lastTime = 0;
  private frameCount = 0;
  private lastFpsTime = 0;

  ngOnInit() {
    this.apiService.getHealth().subscribe({
      next: (res) => this.healthStatus = res.status,
      error: (err) => this.healthStatus = 'Error: ' + err.message
    });

    this.initWebSocket();
    this.startAnimation();
  }

  ngOnDestroy() {
    if (this.ws) {
      this.ws.close();
    }
    if (this.animationId) {
      cancelAnimationFrame(this.animationId);
    }
  }

  private initWebSocket() {
    this.ws = new WebSocket('ws://localhost:8000/ws');

    this.ws.onopen = () => {
      console.log('WebSocket connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'NEW_CAT') {
        this.addCatToCanvas(data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket disconnected');
    };
  }

  private addCatToCanvas(catData: any) {
    const cat: Cat = {
      id: catData.id,
      x: catData.x || Math.random() * 700,
      y: catData.y || Math.random() * 500,
      vx: (Math.random() - 0.5) * 4,
      vy: (Math.random() - 0.5) * 4,
      size: 30 + Math.random() * 20
    };
    this.cats.push(cat);
  }

  addCat() {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'ADD_CAT',
        x: Math.random() * 700,
        y: Math.random() * 500
      }));
    }
  }

  addMultipleCats() {
    for (let i = 0; i < 10; i++) {
      setTimeout(() => this.addCat(), i * 100);
    }
  }

  addCatAtPosition(event: MouseEvent) {
    const rect = this.canvasRef.nativeElement.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({
        type: 'ADD_CAT',
        x: x,
        y: y
      }));
    }
  }

  private startAnimation() {
    const canvas = this.canvasRef.nativeElement;
    const ctx = canvas.getContext('2d')!;

    const animate = (currentTime: number) => {
      // FPS計算
      this.frameCount++;
      if (currentTime - this.lastFpsTime >= 1000) {
        this.fps = this.frameCount;
        this.frameCount = 0;
        this.lastFpsTime = currentTime;
      }

      // キャンバスクリア
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 重力と物理演算
      const gravity = 0.2;
      const friction = 0.98;
      const bounce = 0.7;

      this.cats.forEach(cat => {
        // 重力適用
        cat.vy += gravity;

        // 速度更新
        cat.x += cat.vx;
        cat.y += cat.vy;

        // 摩擦
        cat.vx *= friction;
        cat.vy *= friction;

        // 境界チェック
        if (cat.x <= 0 || cat.x >= canvas.width - cat.size) {
          cat.vx *= -bounce;
          cat.x = Math.max(0, Math.min(canvas.width - cat.size, cat.x));
        }

        if (cat.y >= canvas.height - cat.size) {
          cat.vy *= -bounce;
          cat.y = canvas.height - cat.size;
        }

        // 猫を描画
        this.drawCat(ctx, cat);
      });

      this.animationId = requestAnimationFrame(animate);
    };

    this.animationId = requestAnimationFrame(animate);
  }

  private drawCat(ctx: CanvasRenderingContext2D, cat: Cat) {
    // 猫の顔を描画
    ctx.fillStyle = '#FFA500';
    ctx.beginPath();
    ctx.arc(cat.x + cat.size / 2, cat.y + cat.size / 2, cat.size / 2, 0, Math.PI * 2);
    ctx.fill();

    // 耳
    ctx.fillStyle = '#FF8C00';
    ctx.beginPath();
    ctx.moveTo(cat.x + cat.size / 4, cat.y + cat.size / 4);
    ctx.lineTo(cat.x + cat.size / 3, cat.y);
    ctx.lineTo(cat.x + cat.size / 2, cat.y + cat.size / 4);
    ctx.fill();

    ctx.beginPath();
    ctx.moveTo(cat.x + cat.size * 3 / 4, cat.y + cat.size / 4);
    ctx.lineTo(cat.x + cat.size * 2 / 3, cat.y);
    ctx.lineTo(cat.x + cat.size / 2, cat.y + cat.size / 4);
    ctx.fill();

    // 目
    ctx.fillStyle = '#000';
    ctx.beginPath();
    ctx.arc(cat.x + cat.size / 3, cat.y + cat.size / 3, 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.arc(cat.x + cat.size * 2 / 3, cat.y + cat.size / 3, 2, 0, Math.PI * 2);
    ctx.fill();

    // 鼻
    ctx.fillStyle = '#FF69B4';
    ctx.beginPath();
    ctx.arc(cat.x + cat.size / 2, cat.y + cat.size / 2, 1, 0, Math.PI * 2);
    ctx.fill();
  }
}
