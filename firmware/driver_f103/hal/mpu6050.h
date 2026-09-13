/**
 * @file    mpu6050.h
 * @brief   MPU6050 六轴传感器 I2C 驱动 (互补滤波求俯仰角)
 *
 * I2C 地址 0x68 (AD0 接地)。
 * 输出: 俯仰角(度)、俯仰角速度(度/秒)、偏航角速度(度/秒)。
 *
 * 注意: 俯仰轴与芯片安装方向有关, 上板后需实测校准 (见 .c 里 AXIS 注释)。
 */

#ifndef MPU6050_H
#define MPU6050_H

#include <stdint.h>

typedef struct {
    void *hi2c;       /* I2C_HandleTypeDef* */
    float pitch_deg;  /* 俯仰角 (度, 互补滤波后) */
    float pitch_rate; /* 俯仰角速度 (度/秒) */
    float yaw_rate;   /* 偏航角速度 (度/秒) */
    float dt;         /* 滤波周期 (秒) */
    float alpha;      /* 互补滤波系数 (0.98 = 信任陀螺仪) */
    int   first;      /* 首次读取标志 */
} Mpu6050;

/** 初始化 (唤醒 + 配置量程) */
void mpu6050_init(Mpu6050 *imu, void *hi2c, float dt);

/** 读取并更新姿态 (每个控制周期调用一次) */
void mpu6050_update(Mpu6050 *imu);

#endif /* MPU6050_H */
