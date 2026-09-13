/**
 * @file    mpu6050.c
 * @brief   MPU6050 驱动实现 (互补滤波)
 *
 * 寄存器:
 *   PWR_MGMT_1   0x6B  唤醒
 *   ACCEL_XOUT_H 0x3B  加速度计 (6 字节, 大端)
 *   GYRO_XOUT_H  0x43  陀螺仪   (6 字节)
 *   GYRO_CONFIG  0x1B  ±250°/s -> LSB = 131
 *   ACCEL_CONFIG 0x1C  ±2g     -> LSB = 16384
 *
 * AXIS 约定 (需上板实测校准):
 *   俯仰 = 绕 Y 轴 (芯片 X 轴指向前进方向)
 *   俯仰角速度 = gyro Y (gy)
 *   偏航角速度 = gyro Z (gz)
 */

#include "mpu6050.h"
#include "stm32f1xx_hal.h"
#include <math.h>

#define MPU6050_ADDR        0x68u
#define REG_PWR_MGMT_1      0x6Bu
#define REG_GYRO_CONFIG     0x1Bu
#define REG_ACCEL_CONFIG    0x1Cu
#define REG_ACCEL_XOUT_H    0x3Bu
#define REG_GYRO_XOUT_H     0x43u

#define GYRO_LSB_PER_DEG    131.0f   /* ±250°/s */
#define ACCEL_LSB_PER_G     16384.0f /* ±2g */

#define DEG_PER_RAD         57.2957795f

static void mpu6050_write_reg(Mpu6050 *imu, uint8_t reg, uint8_t val)
{
    I2C_HandleTypeDef *hi2c = (I2C_HandleTypeDef *)imu->hi2c;
    HAL_I2C_Mem_Write(hi2c, (uint16_t)(MPU6050_ADDR << 1), reg,
                      I2C_MEMADD_SIZE_8BIT, &val, 1, 100);
}

static void mpu6050_read_regs(Mpu6050 *imu, uint8_t reg, uint8_t *buf, uint16_t len)
{
    I2C_HandleTypeDef *hi2c = (I2C_HandleTypeDef *)imu->hi2c;
    HAL_I2C_Mem_Read(hi2c, (uint16_t)(MPU6050_ADDR << 1), reg,
                     I2C_MEMADD_SIZE_8BIT, buf, len, 100);
}

void mpu6050_init(Mpu6050 *imu, void *hi2c, float dt)
{
    imu->hi2c = hi2c;
    imu->dt = dt;
    imu->alpha = 0.98f;
    imu->pitch_deg = 0.0f;
    imu->pitch_rate = 0.0f;
    imu->yaw_rate = 0.0f;
    imu->first = 1;

    /* 唤醒 (清除 SLEEP 位) */
    mpu6050_write_reg(imu, REG_PWR_MGMT_1, 0x00);
    /* 陀螺仪 ±250°/s, 加速度计 ±2g */
    mpu6050_write_reg(imu, REG_GYRO_CONFIG, 0x00);
    mpu6050_write_reg(imu, REG_ACCEL_CONFIG, 0x00);
}

void mpu6050_update(Mpu6050 *imu)
{
    uint8_t abuf[6];
    uint8_t gbuf[6];

    mpu6050_read_regs(imu, REG_ACCEL_XOUT_H, abuf, 6);
    mpu6050_read_regs(imu, REG_GYRO_XOUT_H, gbuf, 6);

    /* 大端 -> int16 */
    int16_t ax = (int16_t)((abuf[0] << 8) | abuf[1]);
    int16_t ay = (int16_t)((abuf[2] << 8) | abuf[3]);
    int16_t az = (int16_t)((abuf[4] << 8) | abuf[5]);
    int16_t gx = (int16_t)((gbuf[0] << 8) | gbuf[1]);
    int16_t gy = (int16_t)((gbuf[2] << 8) | gbuf[3]);
    int16_t gz = (int16_t)((gbuf[4] << 8) | gbuf[5]);

    /* 角速度 (度/秒) */
    float gyro_pitch = (float)gy / GYRO_LSB_PER_DEG;   /* 绕 Y */
    float gyro_yaw   = (float)gz / GYRO_LSB_PER_DEG;   /* 绕 Z */

    /* 加速度计俯仰角: pitch = atan2(-ax, sqrt(ay^2+az^2))
     * 芯片水平、X 轴向前时成立; 竖直安装需调整 (见 README) */
    float axg = (float)ax / ACCEL_LSB_PER_G;
    float ayg = (float)ay / ACCEL_LSB_PER_G;
    float azg = (float)az / ACCEL_LSB_PER_G;
    float accel_pitch = atan2f(-axg, sqrtf(ayg * ayg + azg * azg)) * DEG_PER_RAD;

    /* 互补滤波 */
    if (imu->first) {
        imu->pitch_deg = accel_pitch;
        imu->first = 0;
    } else {
        imu->pitch_deg = imu->alpha * (imu->pitch_deg + gyro_pitch * imu->dt)
                       + (1.0f - imu->alpha) * accel_pitch;
    }

    imu->pitch_rate = gyro_pitch;
    imu->yaw_rate   = gyro_yaw;
}
