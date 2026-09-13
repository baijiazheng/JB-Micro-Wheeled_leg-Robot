/**
 * @file    test_foc_control.c
 * @brief   FOC 控制环 + 电机模型的 PC 端仿真测试
 *
 * 编译: gcc -o test_foc_control test_foc_control.c foc_control.c foc_math.c ../common/pid/pid.c -lm
 *   (在 foc/ 目录下: gcc -o test_foc_control test_foc_control.c foc_control.c foc_math.c ../../common/pid/pid.c -lm)
 *
 * 验证:
 *   1. 编码器角度解绕 (跨 0/2pi 不跳变)
 *   2. 速度估计 (匀速旋转 -> 估算收敛到真实值)
 *   3. 速度闭环 (PID + 电压FOC + 简单电机模型 -> 收敛到目标转速)
 */

#include <stdio.h>
#include <math.h>
#include "foc_control.h"
#include "../../common/pid/pid.h"

static int g_fail = 0;
#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("  [FAIL] "); printf(__VA_ARGS__); printf("\n"); g_fail++; } \
    else         { printf("  [ OK ] "); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

/* 简单电机模型: J*w_dot = K*Vq - B*w  (电压模式, 忽略反电动势细节) */
typedef struct {
    float J;   /* 转动惯量 */
    float K;   /* 电压->扭矩系数 */
    float B;   /* 阻尼 */
    float w;   /* 机械角速度 rad/s */
    float mech_angle; /* 机械角 rad, 0..2pi */
} MotorModel;

static void motor_step(MotorModel *m, float vq, float dt)
{
    float w_dot = (m->K * vq - m->B * m->w) / m->J;
    m->w += w_dot * dt;
    m->mech_angle += m->w * dt;
    /* 绕回 [0, 2pi) */
    while (m->mech_angle >= TWO_PI) m->mech_angle -= TWO_PI;
    while (m->mech_angle < 0)       m->mech_angle += TWO_PI;
}

int main(void)
{
    printf("========== FOC 控制环仿真测试 ==========\n\n");

    /* ---- 1. 角度解绕 ---- */
    printf("[1] 编码器角度解绕 (跨 0/2pi)\n");
    {
        FocControl fc;
        foc_control_init(&fc, 7, 0.001f, 0.1f);
        /* 模拟匀速旋转跨过 0 点: 从 0 开始每次步进 0.3 rad (真实采样场景) */
        float mech = 0.0f;
        float accum_last = 0.0f;
        int ok = 1;
        int crossings = 0;
        for (int k = 0; k < 25; k++) {
            mech += 0.3f;
            if (mech >= TWO_PI) { mech -= TWO_PI; crossings++; }
            float elec = foc_control_encoder_update(&fc, mech);
            (void)elec;
            float d = fc.mech_angle_accum - accum_last;
            if (d <= 0.0f || d > 0.31f) ok = 0; /* 每步应是 ~0.3 的正增量 */
            accum_last = fc.mech_angle_accum;
        }
        CHECK(ok && crossings > 0, "跨 0 点 %d 次, 角度连续累加不跳变", crossings);
    }

    /* ---- 2. 速度估计 ---- */
    printf("\n[2] 速度估计 (匀速 10 rad/s)\n");
    {
        FocControl fc;
        foc_control_init(&fc, 7, 0.001f, 0.1f);
        MotorModel m = {0.001f, 1.0f, 0.01f, 0.0f, 0.0f};
        /* 直接让电机匀速旋转: 手动推角度 */
        float w_true = 10.0f;
        float mech = 0.0f;
        float est = 0.0f;
        for (int k = 0; k < 2000; k++) {
            mech += w_true * 0.001f;
            while (mech >= TWO_PI) mech -= TWO_PI;
            foc_control_encoder_update(&fc, mech);
            est = fc.velocity;
            (void)m;
        }
        CHECK(fabsf(est - w_true) < 0.5f, "估算速度 %.3f ≈ 真实 %.3f", est, w_true);
    }

    /* ---- 3. 速度闭环 ---- */
    printf("\n[3] 速度闭环 (目标 20 rad/s, 收敛检查)\n");
    {
        FocControl fc;
        foc_control_init(&fc, 7, 0.001f, 0.15f);
        MotorModel m = {0.001f, 1.0f, 0.01f, 0.0f, 0.0f};

        PIDController pid;
        pid_init(&pid, 0.5f, 2.0f, 0.0f, 1.0f, 0.001f); /* Vq 限幅 ±1 */

        float target = 20.0f;
        float final_w = 0.0f;
        for (int k = 0; k < 5000; k++) {
            /* 1. 编码器更新 -> 速度估计 + 电角度 */
            float theta_elec = foc_control_encoder_update(&fc, m.mech_angle);
            /* 2. 速度 PID -> Vq */
            float vq = pid_update(&pid, target, fc.velocity);
            /* 3. FOC 电压 -> 占空比 (只验证合法, 不反馈到模型) */
            DutyCycle d = foc_control_voltage_step(theta_elec, vq, 0.0f);
            if (d.a < 0 || d.a > 1 || d.b < 0 || d.b > 1 || d.c < 0 || d.c > 1) {
                CHECK(0, "闭环中占空比越界 (k=%d)", k);
                break;
            }
            /* 4. 电机模型响应 Vq */
            motor_step(&m, vq, 0.001f);
            final_w = m.w;
        }
        printf("  最终转速 = %.3f rad/s (目标 %.1f)\n", final_w, target);
        CHECK(fabsf(final_w - target) < 1.0f, "速度闭环收敛到目标 (误差 %.3f)", fabsf(final_w - target));
    }

    printf("\n========================================\n");
    if (g_fail == 0) { printf("全部测试通过 ✅\n"); return 0; }
    else { printf("%d 项失败 ❌\n", g_fail); return 1; }
}
