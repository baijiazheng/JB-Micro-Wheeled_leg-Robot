/**
 * @file    foc_math.c
 * @brief   FOC 核心数学实现 (纯 C, 无硬件依赖)
 *
 * 所有变换幅度不变 (amplitude-invariant)，电压/电流归一化到 [-1,1]。
 *
 * ============ 空间矢量 (SVPWM) 原理简述 ============
 * 三相逆变器 (如 L6234) 有 8 个开关状态：
 *   6 个"有效矢量"(形成六边形的 6 个顶点) + 2 个"零矢量"(000, 111)。
 * 任意目标电压矢量 V = (V_alpha, V_beta) 落在六边形内，可以分解为
 * 所在扇区相邻两个有效矢量按时间加权 + 零矢量补足。
 *
 * 经典做法是"扇区法"：先判断 V 落在 6 个扇区中的哪个，再算两个有效矢量的
 * 作用时间 T1/T2。这里采用与之**数学完全等价**的"零序注入法"(min-max)，
 * 因为它更简洁、更不易错，工业上大量使用：
 *
 *   1. 反 Clarke 得到三相电压 Va,Vb,Vc
 *   2. 注入零序分量 Voffset = -(max + min)/2  (相当于叠加三次谐波)
 *   3. 平移到 [0,1] 即得三相占空比
 *
 * 叠加三次谐波后相电压仍是正弦(线电压不变)，却把线性调制范围从
 * 1/sqrt(3)≈0.577 提升到 1/sqrt(3)*2/sqrt(3)... 即提升约 15% 母线利用率。
 */

#include "foc_math.h"

/* ============ Clarke 变换: abc -> alpha,beta ============ */
AlphaBeta clarke_transform(float ia, float ib, float ic)
{
    AlphaBeta out;
    /* 幅度不变 Clarke (通用三相形式, 不平衡也成立):
     *   alpha = (2*ia - ib - ic) / 3
     *   beta  = (ib - ic) / sqrt(3)
     * 平衡时 (ia+ib+ic=0) 自动退化为 alpha=ia, beta=(ia+2ib)/sqrt(3)
     */
    out.alpha = (2.0f * ia - ib - ic) / 3.0f;
    out.beta  = (ib - ic) * ONE_OVER_SQRT3;
    return out;
}

/* ============ 反 Clarke: alpha,beta -> abc ============ */
Phase3f inverse_clarke(float valpha, float vbeta)
{
    Phase3f out;
    out.a = valpha;
    out.b = -0.5f * valpha + (SQRT3 / 2.0f) * vbeta;
    out.c = -0.5f * valpha - (SQRT3 / 2.0f) * vbeta;
    return out;
}

/* ============ Park 变换: alpha,beta -> d,q ============ */
Dq park_transform(float ialpha, float ibeta, float theta)
{
    Dq out;
    float c = cosf(theta);
    float s = sinf(theta);
    out.d =  ialpha * c + ibeta * s;
    out.q = -ialpha * s + ibeta * c;
    return out;
}

/* ============ 反 Park 变换: d,q -> alpha,beta ============ */
AlphaBeta inverse_park(float vd, float vq, float theta)
{
    AlphaBeta out;
    float c = cosf(theta);
    float s = sinf(theta);
    out.alpha = vd * c - vq * s;
    out.beta  = vd * s + vq * c;
    return out;
}

/* ============ SVPWM: alpha,beta -> 三相占空比 [0,1] ============ */
DutyCycle svpwm(float valpha, float vbeta)
{
    /* 1. 反 Clarke: 得到三相相电压 (归一化, [-1,1]) */
    Phase3f v = inverse_clarke(valpha, vbeta);

    /* 2. 零序注入 (min-max) */
    float vmax = v.a;
    float vmin = v.a;
    if (v.b > vmax) vmax = v.b;
    if (v.c > vmax) vmax = v.c;
    if (v.b < vmin) vmin = v.b;
    if (v.c < vmin) vmin = v.c;

    float voffset = -(vmax + vmin) / 2.0f;
    v.a += voffset;
    v.b += voffset;
    v.c += voffset;

    /* 3. 平移到占空比 [0,1]: -1->0, +1->1 */
    DutyCycle duty;
    duty.a = (v.a + 1.0f) / 2.0f;
    duty.b = (v.b + 1.0f) / 2.0f;
    duty.c = (v.c + 1.0f) / 2.0f;

    /* 4. 数值保护 (钳位到 [0,1]) */
    if (duty.a < 0.0f) duty.a = 0.0f;
    if (duty.a > 1.0f) duty.a = 1.0f;
    if (duty.b < 0.0f) duty.b = 0.0f;
    if (duty.b > 1.0f) duty.b = 1.0f;
    if (duty.c < 0.0f) duty.c = 0.0f;
    if (duty.c > 1.0f) duty.c = 1.0f;

    return duty;
}
