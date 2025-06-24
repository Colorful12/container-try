import { Component, OnInit, OnDestroy, ViewChild, ElementRef, inject } from '@angular/core';
import { ApiService } from './api.service';
import { HttpClientModule } from '@angular/common/http';

interface CatData {
  id: string;
  x?: number;
  y?: number;
}

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
      console.log('【taki】WebSocket connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'NEW_CAT') {
        this.addCatToCanvas(data);
      }
    };

    this.ws.onerror = (error) => {
      console.error('【taki】WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('【taki】WebSocket disconnected');
    };
  }

  private addCatToCanvas(catData: CatData) {
    const cat: Cat = {
      id: catData.id,
      x: catData.x || Math.random() * 700,
      y: catData.y || Math.random() * 500,
      vx: (Math.random() - 0.5) * 8,
      vy: (Math.random() - 0.5) * 8,
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

  addLoadTestCats() {
    console.log('【taki】🔥 Starting Load Test: 100 cats');
    for (let i = 0; i < 100; i++) {
      setTimeout(() => this.addCat(), i * 50); // より速く追加
    }
  }

  addExtremeLoadTest() {
    console.log('【taki】💥 Starting Extreme Load Test: 500 cats');
    for (let i = 0; i < 500; i++) {
      setTimeout(() => this.addCat(), i * 20); // 非常に速く追加
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

      // 物理演算（重力なし、完全反射、エネルギー保存）
      const bounce = 1.0;     // 完全反射

      this.cats.forEach(cat => {
        // 速度更新
        cat.x += cat.vx;
        cat.y += cat.vy;

        // 摩擦なし（エネルギー完全保存）
        // cat.vx *= friction;  // コメントアウト
        // cat.vy *= friction;  // コメントアウト

        // 境界チェックと完全反射
        if (cat.x <= 0) {
          cat.vx = Math.abs(cat.vx) * bounce; // 右向きに反射
          cat.x = 0;
        } else if (cat.x >= canvas.width - cat.size) {
          cat.vx = -Math.abs(cat.vx) * bounce; // 左向きに反射
          cat.x = canvas.width - cat.size;
        }

        if (cat.y <= 0) {
          cat.vy = Math.abs(cat.vy) * bounce; // 下向きに反射
          cat.y = 0;
        } else if (cat.y >= canvas.height - cat.size) {
          cat.vy = -Math.abs(cat.vy) * bounce; // 上向きに反射
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
