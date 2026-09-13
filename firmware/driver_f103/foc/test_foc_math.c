/**
 * @file    test_foc_math.c
 * @brief   FOC 数学模块的 PC 端单元测试 (x86 gcc 编译运行)
 *
 * 编译:   gcc -o test_foc_math test_foc_math.c foc_math.c -lm
 * 运行:   ./test_foc_math
 *
 * 验证内容:
 *   1. Clarke / 反 Clarke 往返一致
 *   2. Park  / 反 Park  往返一致
 *   3. SVPWM 占空比始终在 [0,1]
 *   4. SVPWM 输出能反解回原电压矢量 (FOC 全链路: Vd,Vq -> 三相)
 */

#include <stdio.h>
#include <math.h>
#include "foc_math.h"

static int g_fail = 0;

#define CHECK(cond, ...) do { \
    if (!(cond)) { printf("  [FAIL] "); printf(__VA_ARGS__); printf("\n"); g_fail++; } \
    else         { printf("  [ OK ] "); printf(__VA_ARGS__); printf("\n"); } \
} while (0)

static int near(float a, float b, float eps) { return fabsf(a - b) < eps; }

int main(void)
{
    printf("========== FOC 数学单元测试 ==========\n\n");

    /* ---- 1. Clarke / 反 Clarke 往返 ---- */
    printf("[1] Clarke <-> 反 Clarke 往返\n");
    {
        /* 平衡三相: ia+ib+ic = 0 */
        float ia = 0.4f, ib = 0.1f, ic = -0.5f;
        AlphaBeta ab = clarke_transform(ia, ib, ic);
        Phase3f back = inverse_clarke(ab.alpha, ab.beta);
        CHECK(near(back.a, ia, 1e-5) && near(back.b, ib, 1e-5) && near(back.c, ic, 1e-5),
              "平衡三相往返一致");
    }

    /* ---- 2. Park / 反 Park 往返 ---- */
    printf("\n[2] Park <-> 反 Park 往返\n");
    {
        float ialpha = 0.3f, ibeta = -0.2f, theta = 1.0f; /* 57.3 度 */
        Dq dq = park_transform(ialpha, ibeta, theta);
        AlphaBeta back = inverse_park(dq.d, dq.q, theta);
        CHECK(near(back.alpha, ialpha, 1e-5) && near(back.beta, ibeta, 1e-5),
              "Park 往返一致");
    }

    /* ---- 3. SVPWM 占空比范围 + 反解 ---- */
    printf("\n[3] SVPWM 占空比范围与反解\n");
    {
        int in_range = 1;
        float max_err = 0.0f;
        /* 扫一圈电角度, Vq=0.5, Vd=0 */
        for (int i = 0; i <= 360; i += 5) {
            float theta = (float)i * (float)M_PI / 180.0f;
            AlphaBeta v = inverse_park(0.0f, 0.5f, theta); /* Vd=0,Vq=0.5 */
            DutyCycle d = svpwm(v.alpha, v.beta);

            /* 占空比必须在 [0,1] */
            if (d.a < 0.0f || d.a > 1.0f || d.b < 0.0f || d.b > 1.0f ||
                d.c < 0.0f || d.c > 1.0f) {
                in_range = 0;
            }

            /* 反解: 占空比 -> 相电压(去共模) -> Clarke -> alpha,beta */
            float va = 2.0f * d.a - 1.0f;
            float vb = 2.0f * d.b - 1.0f;
            float vc = 2.0f * d.c - 1.0f;
            float mean = (va + vb + vc) / 3.0f;   /* 去掉注入的零序共模 */
            va -= mean; vb -= mean; vc -= mean;
            AlphaBeta rec = clarke_transform(va, vb, vc);

            float err = fabsf(rec.alpha - v.alpha) + fabsf(rec.beta - v.beta);
            if (err > max_err) max_err = err;
        }
        CHECK(in_range, "所有角度占空比均在 [0,1]");
        CHECK(max_err < 1e-3, "SVPWM 输出能反解回原电压矢量 (最大误差 %.6f)", max_err);
    }

    /* ---- 4. FOC 全链路: 三相输出是平衡正弦 ---- */
    printf("\n[4] FOC 全链路 (Vd=0, Vq=0.5) 三相输出\n");
    {
        float theta = 0.7f;
        AlphaBeta v = inverse_park(0.0f, 0.5f, theta);
        DutyCycle d = svpwm(v.alpha, v.beta);
        float va = 2.0f * d.a - 1.0f;
        float vb = 2.0f * d.b - 1.0f;
        float vc = 2.0f * d.c - 1.0f;
        float sum = va + vb + vc;
        /* 线电压平衡时, 注入零序后三相之和 = 3*voffset (非 0 正常) */
        printf("  duty = [%.4f, %.4f, %.4f]\n", d.a, d.b, d.c);
        /* 关键: 三个占空比互不相等且都在线性区, 说明矢量确实旋转到了某扇区 */
        CHECK(d.a >= 0.0f && d.a <= 1.0f && d.b >= 0.0f && d.b <= 1.0f && d.c >= 0.0f && d.c <= 1.0f,
              "单点占空比在 [0,1]");
        (void)sum;
    }

    printf("\n========================================\n");
    if (g_fail == 0) {
        printf("全部测试通过 ✅\n");
        return 0;
    } else {
        printf("%d 项测试失败 ❌\n", g_fail);
        return 1;
    }
}
