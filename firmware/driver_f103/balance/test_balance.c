/**
 * @file    test_balance.c
 * @brief   LQR 平衡控制器 + 倒立摆模型的 PC 仿真
 *
 * 编译(在 balance/ 目录):
 *   gcc -o test_balance test_balance.c balance.c ../../common/pid/pid.c -lm
 *
 * 验证:
 *   1. 从倾斜 5° 起步, 控制器能扶正 (theta -> 0)
 *   2. 稳定后施加"踹一脚"扰动, 能恢复
 *   3. 位移被约束在原点附近 (原地保持)
 */

#include <stdio.h>
#include <math.h>
#include "balance.h"

static int g_fail = 0;
#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("  [FAIL] "); printf(__VA_ARGS__); printf("\n"); g_fail++; } \
    else         { printf("  [ OK ] "); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

/* 倒立摆小车模型 (线性化, 角度单位: 度)
 *   theta_ddot = A*theta + B*u    (重力失稳 + 控制转矩)
 *   x_ddot     = C*u              (轮子受转矩加速)
 */
typedef struct {
    float theta;   /* 俯仰角 (度) */
    float dtheta;  /* 俯仰角速度 (度/秒) */
    float x;       /* 位移 */
    float dx;      /* 速度 */
} Pendulum;

static void pendulum_step(Pendulum *p, float u, float dt,
                          float A, float B, float C)
{
    /* theta_ddot = A*theta - B*u  (u=前向加速度, 前向加速 -> 后仰, 负耦合) */
    float theta_ddot = A * p->theta - B * u;
    float x_ddot = C * u;
    p->dtheta += theta_ddot * dt;
    p->theta += p->dtheta * dt;
    p->dx += x_ddot * dt;
    p->x += p->dx * dt;
}

int main(void)
{
    printf("========== LQR 平衡控制器仿真 ==========\n\n");

    const float dt = 0.001f;       /* 1kHz 控制周期 */
    const float A = 30.0f, B = 50.0f, C = 20.0f;  /* 摆模型参数 */

    /* 仿真增益: 由 LQR 黎卡提方程解出 (Q=diag[10,1,0.01,0.01], R=1)
     * 这是"正确"的联合增益, 不是手调的四路独立 PID */
    const float KP_ANGLE = 4.87f, KD_GYRO = 1.21f;
    const float KP_DIST  = 0.10f, KD_SPEED = 0.285f;

    /* ---- 1. 扶正 ---- */
    printf("[1] 从 5° 倾斜扶正\n");
    {
        BalanceController bc;
        balance_init(&bc, dt);
        bc.angle_zero = 0.0f; /* 仿真按竖直平衡 */
        bc.pid_angle.kp = KP_ANGLE;
        bc.pid_gyro.kp  = KD_GYRO;
        bc.pid_distance.kp = KP_DIST;
        bc.pid_speed.kp = KD_SPEED;

        Pendulum p = {5.0f, 0.0f, 0.0f, 0.0f}; /* 初始倾斜 5 度 */
        float last_theta = 0.0f;
        int settled = 0;
        for (int k = 0; k < 5000; k++) {
            float u = balance_update(&bc, p.theta, p.dtheta, p.x, p.dx, 0.0f);
            pendulum_step(&p, u, dt, A, B, C);
            last_theta = p.theta;
            if (fabsf(p.theta) < 0.5f) settled++;
            else settled = 0;
        }
        CHECK(fabsf(last_theta) < 1.0f, "最终俯仰角 %.3f° (收敛到竖直)", last_theta);
        CHECK(fabsf(p.x) < 10.0f, "位移被约束在原点附近 (x=%.2f)", p.x);
    }

    /* ---- 2. 抗扰动 (踹一脚) ---- */
    printf("\n[2] 稳定后施加扰动 (踹一脚) 恢复\n");
    {
        BalanceController bc;
        balance_init(&bc, dt);
        bc.angle_zero = 0.0f;
        bc.pid_angle.kp = KP_ANGLE;
        bc.pid_gyro.kp  = KD_GYRO;
        bc.pid_distance.kp = KP_DIST;
        bc.pid_speed.kp = KD_SPEED;

        Pendulum p = {0.0f, 0.0f, 0.0f, 0.0f};
        /* 先稳定 2000 步 */
        for (int k = 0; k < 2000; k++) {
            float u = balance_update(&bc, p.theta, p.dtheta, p.x, p.dx, 0.0f);
            pendulum_step(&p, u, dt, A, B, C);
        }
        /* 踹一脚: 突然给 4° 扰动 */
        p.theta += 4.0f;
        float max_theta = 0.0f;
        for (int k = 0; k < 3000; k++) {
            float u = balance_update(&bc, p.theta, p.dtheta, p.x, p.dx, 0.0f);
            pendulum_step(&p, u, dt, A, B, C);
            if (fabsf(p.theta) > max_theta) max_theta = fabsf(p.theta);
        }
        CHECK(fabsf(p.theta) < 1.0f, "扰动后恢复 (最终 %.3f°, 峰值 %.2f°)", p.theta, max_theta);
    }

    /* ---- 3. 前进目标速度 ---- */
    printf("\n[3] 前进速度跟踪 (目标 2.0)\n");
    {
        BalanceController bc;
        balance_init(&bc, dt);
        bc.angle_zero = 0.0f;
        bc.pid_angle.kp = KP_ANGLE;
        bc.pid_gyro.kp  = KD_GYRO;
        bc.pid_distance.kp = KP_DIST;  /* 用实际增益, 位移零点重置逻辑自动处理运动 */
        bc.pid_speed.kp = KD_SPEED;

        Pendulum p = {0.0f, 0.0f, 0.0f, 0.0f};
        float final_dx = 0.0f;
        for (int k = 0; k < 8000; k++) {
            float u = balance_update(&bc, p.theta, p.dtheta, p.x, p.dx, 2.0f);
            pendulum_step(&p, u, dt, A, B, C);
            final_dx = p.dx;
            /* 若倾角过大(失控)提前退出 */
            if (fabsf(p.theta) > 15.0f) { final_dx = -999.0f; break; }
        }
        CHECK(fabsf(p.theta) < 3.0f && fabsf(final_dx - 2.0f) < 1.0f,
              "边平衡边前进 (theta=%.2f°, 速度=%.2f)", p.theta, final_dx);
    }

    printf("\n========================================\n");
    if (g_fail == 0) { printf("全部测试通过 ✅\n"); return 0; }
    else { printf("%d 项失败 ❌\n", g_fail); return 1; }
}
