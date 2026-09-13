/**
 * @file    foc_math.h
 * @brief   FOC 核心数学 (Clarke / Park / 反变换 / SVPWM)
 *
 * 本模块是从零实现 FOC 的第一层：纯数学、与硬件无关。
 * 它跑在 STM32 上，也可以直接在 PC (x86 gcc) 上编译测试 (见 test_foc_math.c)。
 *
 * 学习路径 (由外到内):
 *   1. Clarke  变换: 三相(a,b,c) -> 两相正交(alpha,beta)
 *   2. Park    变换: 静止(alpha,beta) -> 旋转(d,q)  [随转子角度旋转]
 *   3. 反 Park 变换: 旋转(d,q) -> 静止(alpha,beta)   [FOC 用这个把 Vd,Vq 变回电压]
 *   4. 反 Clarke:   静止(alpha,beta) -> 三相电压
 *   5. SVPWM:       由 V_alpha,V_beta 算出三相占空比 (空间矢量调制)
 *
 * 约定:
 *   - 幅度不变 (amplitude-invariant) Clarke/Park，系数不含 2/3
 *   - 角度 theta 单位为弧度，为电角度 (机械角 x 极对数)
 *   - Vd/Vq、V_alpha/V_beta 都归一化到 [-1, 1] (相对母线电压 Vdc)
 */

#ifndef FOC_MATH_H
#define FOC_MATH_H

#include <math.h>

#define SQRT3       1.7320508075688772935f  /* sqrt(3) */
#define ONE_OVER_SQRT3 0.5773502691896258f  /* 1/sqrt(3) */
#define TWO_PI      6.283185307179586f

/* ---- 结构体: 三相量 ---- */
typedef struct {
    float a;
    float b;
    float c;
} Phase3f;

/* ---- 结构体: 两相静止 (alpha, beta) ---- */
typedef struct {
    float alpha;
    float beta;
} AlphaBeta;

/* ---- 结构体: 两相旋转 (d, q) ---- */
typedef struct {
    float d;
    float q;
} Dq;

/* ---- 结构体: 三相占空比 [0,1] ---- */
typedef struct {
    float a;
    float b;
    float c;
} DutyCycle;

/* ============ 变换函数 ============ */

/** Clarke: 三相电流 -> alpha,beta (幅度不变) */
AlphaBeta clarke_transform(float ia, float ib, float ic);

/** 反 Clarke: alpha,beta -> 三相电压 */
Phase3f inverse_clarke(float valpha, float vbeta);

/** Park: alpha,beta -> d,q (theta 为电角度, 弧度) */
Dq park_transform(float ialpha, float ibeta, float theta);

/** 反 Park: d,q -> alpha,beta (theta 为电角度, 弧度) */
AlphaBeta inverse_park(float vd, float vq, float theta);

/* ============ SVPWM ============ */

/**
 * SVPWM: 由 alpha,beta 电压算出三相占空比 [0,1]
 * 输入 V_alpha,V_beta 归一化到 [-1,1] (相对 Vdc)。
 * 输出为占空比 (0.0 = 下桥全开, 1.0 = 上桥全开)。
 */
DutyCycle svpwm(float valpha, float vbeta);

#endif /* FOC_MATH_H */
