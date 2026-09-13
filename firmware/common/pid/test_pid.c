/**
 * @file    test_pid.c
 * @brief   PID 控制器 PC 端单元测试
 *
 * 编译: gcc -o test_pid test_pid.c pid.c -lm
 */

#include <stdio.h>
#include <math.h>
#include "pid.h"

static int g_fail = 0;
#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("  [FAIL] "); printf(__VA_ARGS__); printf("\n"); g_fail++; } \
    else         { printf("  [ OK ] "); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

static int near(float a, float b, float eps) { return fabsf(a - b) < eps; }

int main(void)
{
    printf("========== PID 单元测试 ==========\n\n");

    /* ---- 1. 纯比例 ---- */
    printf("[1] 纯比例响应\n");
    {
        PIDController pid;
        pid_init(&pid, 2.0f, 0.0f, 0.0f, 10.0f, 0.001f);
        float u = pid_update(&pid, 1.0f, 0.0f); /* 误差=1, u=Kp*e=2 */
        CHECK(near(u, 2.0f, 1e-5), "u = Kp*e = %.4f", u);
    }

    /* ---- 2. 输出限幅 ---- */
    printf("\n[2] 输出限幅\n");
    {
        PIDController pid;
        pid_init(&pid, 100.0f, 0.0f, 0.0f, 5.0f, 0.001f);
        float u = pid_update(&pid, 1.0f, 0.0f); /* 100*1=100 -> 限幅到 5 */
        CHECK(near(u, 5.0f, 1e-5), "输出被限幅到 %.4f", u);
    }

    /* ---- 3. 积分累积 ---- */
    printf("\n[3] 积分累积\n");
    {
        PIDController pid;
        pid_init(&pid, 0.0f, 1.0f, 0.0f, 100.0f, 0.1f);
        float u = 0;
        for (int k = 0; k < 10; k++) {
            u = pid_update(&pid, 0.0f, 0.5f); /* 恒定误差 -0.5, 每次积分 +(-0.5*1*0.1)=-0.05 */
        }
        /* 10 次后积分 ≈ -0.5, 输出 ≈ -0.5 */
        CHECK(near(u, -0.5f, 1e-3), "10 次后积分输出 = %.4f (期望 -0.5)", u);
    }

    /* ---- 4. 抗饱和 (积分不无限涨) ---- */
    printf("\n[4] 抗饱和 (积分冻结)\n");
    {
        PIDController pid;
        pid_init(&pid, 1.0f, 10.0f, 0.0f, 2.0f, 0.1f); /* 输出限幅 2 */
        float u = 0;
        for (int k = 0; k < 1000; k++) {
            u = pid_update(&pid, 10.0f, 0.0f); /* 大误差, 会饱和 */
        }
        /* 输出被限幅在 2, 积分被冻结不爆炸 */
        CHECK(u <= 2.0f + 1e-3 && u >= -2.0f - 1e-3, "1000 次后输出仍限幅在 ±2 (当前 %.4f)", u);
    }

    printf("\n========================================\n");
    if (g_fail == 0) { printf("全部测试通过 ✅\n"); return 0; }
    else { printf("%d 项失败 ❌\n", g_fail); return 1; }
}
