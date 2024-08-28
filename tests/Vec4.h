#ifndef Vec4_h
#define Vec4_h

#include "Vec3.h"

template <class T>
class Vec4T{
    using VEC  = Vec4T<T>;
    using VEC3 = Vec3T<T>;
public:
    union{
        struct{ T x, y, z, w; };
        //struct{ T a, b, c, d; };
        struct{ T i, j, k, l; };
        struct{ VEC3 f; T e; };
        T array[4];
    };

    // ===== methods

    Vec4T() = default;
    constexpr Vec4T(T x_, T y_, T z_, T w_) : x(x_), y(y_), z(z_), w(w_) {};
    constexpr Vec4T(const VEC3& vec3, T scalar){  f = vec3;    e = scalar;   }

    inline VEC swaped(const Vec4T<int>& inds) const { return VEC{array[inds.x], array[inds.y], array[inds.z], array[inds.w]}; };
    inline void swap(const Vec4T<int>& inds) { *this = swaped(inds); };

    inline VEC& set(T f) { x = f; y = f; z = f; w = f; return *this; };
    inline VEC& set(T fx, T fy, T fz, T fw) { x = fx; y = fy; z = fz; w = fw; return *this; };
    inline VEC& set(const VEC& v) { x = v.x; y = v.y; z = v.z; w = v.w; return *this; };
    inline VEC& set(T* arr) { x = arr[0]; y = arr[1]; z = arr[2]; w = arr[3]; return *this; };

    inline VEC& get(T& fx, T& fy, T& fz, T& fw) { fx = x; fy = y; fz = z; fw = w; return *this; };
    inline VEC& get(T* arr) { arr[0] = x; arr[1] = y; arr[2] = z; arr[3] = w; return *this; };

    inline VEC& add(T f) { x += f; y += f; z += f; w += f; return *this; };
    inline VEC& mul(T f) { x *= f; y *= f; z *= f; w *= f; return *this; };

    inline VEC& add(const VEC& v) { x += v.x; y += v.y; z += v.z; w += v.w; return *this; };
    inline VEC& sub(const VEC& v) { x -= v.x; y -= v.y; z -= v.z; w -= v.w; return *this; };
    inline VEC& mul(const VEC& v) { x *= v.x; y *= v.y; z *= v.z; w *= v.w; return *this; };
    inline VEC& div(const VEC& v) { x /= v.x; y /= v.y; z /= v.z; w /= v.w; return *this; };

    inline VEC get_inv() { VEC o; o.x = 1 / x; o.y = 1 / y; o.z = 1 / z; o.w = 1 / w; return o; };

    inline void operator+=(const VEC& v) { x += v.x; y += v.y; z += v.z; w += v.w; };
    inline void operator*=(const VEC& v) { x *= v.x; y *= v.y; z *= v.z; w *= v.w; };

    inline VEC operator*(T f) const { return VEC{ x * f, y * f, z * f, w * f }; };

    inline VEC operator+(const VEC& vi) const { return VEC{ x + vi.x, y + vi.y, z + vi.z, w + vi.w }; };
    inline VEC operator-(const VEC& vi) const { return VEC{ x - vi.x, y - vi.y, z - vi.z, w - vi.w }; };
    inline VEC operator*(const VEC& vi) const { return VEC{ x * vi.x, y * vi.y, z * vi.z, w * vi.w }; };
    inline VEC operator/(const VEC& vi) const { return VEC{ x / vi.x, y / vi.y, z / vi.z, w / vi.w }; };

    inline T dot(const VEC& a) const { return x * a.x + y * a.y + z * a.z + w * a.w; };
    inline T norm2() const { return x * x + y * y + z * z + w * w; };
    inline T norm() const { return sqrt(x * x + y * y + z * z + w * w); };

    inline T normalize() {
        T norm = sqrt(x * x + y * y + z * z + w * w);
        T inVnorm = 1.0 / norm;
        x *= inVnorm; y *= inVnorm; z *= inVnorm; w *= inVnorm;
        return norm;
    }
    
    inline VEC normalized() const {
        VEC v; v.set(*this);
        v.normalize();
        return v;
    }
};

using Vec4i = Vec4T<int>;
using Vec4f = Vec4T<float>;
using Vec4d = Vec4T<double>;
using Vec4b = Vec4T<bool>;

static constexpr Vec4d Vec4dZero{ 0.0, 0.0, 0.0, 0.0 };
static constexpr Vec4d Vec4dOne{ 1.0, 1.0, 1.0, 1.0 };
static constexpr Vec4d Vec4dX{ 1.0, 0.0, 0.0, 0.0 };
static constexpr Vec4d Vec4dY{ 0.0, 1.0, 0.0, 0.0 };
static constexpr Vec4d Vec4dZ{ 0.0, 0.0, 1.0, 0.0 };
static constexpr Vec4d Vec4dW{ 0.0, 0.0, 0.0, 1.0 };
static constexpr Vec4d Vec4dmin{ -1e+300, -1e+300, -1e+300, -1e+300 };
static constexpr Vec4d Vec4dmax{ +1e+300, +1e+300, +1e+300, +1e+300 };

static constexpr Vec4f Vec4fZero{ 0.0f, 0.0f, 0.0f, 0.0f };
static constexpr Vec4f Vec4fOne{ 1.0f, 1.0f, 1.0f, 1.0f };
static constexpr Vec4f Vec4fX{ 1.0f, 0.0f, 0.0f, 0.0f };
static constexpr Vec4f Vec4fY{ 0.0f, 1.0f, 0.0f, 0.0f };
static constexpr Vec4f Vec4fZ{ 0.0f, 0.0f, 1.0f, 0.0f };
static constexpr Vec4f Vec4fW{ 0.0f, 0.0f, 0.0f, 1.0f };
static constexpr Vec4f Vec4fmin{ -1e+37f, -1e+37f, -1e+37f, -1e+37f };
static constexpr Vec4f Vec4fmax{ +1e+37f, +1e+37f, +1e+37f, +1e+37f };

template<typename T1, typename T2>
inline void convert(const Vec4T<T1>& i, Vec4T<T2>& o) { o.x = (T2)i.x; o.y = (T2)i.y; o.z = (T2)i.z; o.w = (T2)i.w; };

template<typename T1, typename T2>
inline Vec4T<T2> cast(const Vec4T<T1>& i) { Vec4T<T2> o; o.x = (T2)i.x; o.y = (T2)i.y; o.z = (T2)i.z; o.w = (T2)i.w; return o; };

#endif
