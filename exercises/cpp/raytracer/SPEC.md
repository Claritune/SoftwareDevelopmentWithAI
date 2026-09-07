# SPEC — Mini Ray Tracer

Technical specification for the mini ray tracer. This is the source of truth the Orchestrator agent works from: it defines the modules, the interfaces between them, the feature scope, and the acceptance criteria every agent's work is judged against.

The scope is deliberately trimmed from Peter Shirley's *Ray Tracing in One Weekend*: enough to produce a genuinely nice image, small enough to build live.

---

## 1. Goal

A command-line program that renders a static scene of spheres to an image file. A ray is cast through every pixel, bounced through the scene up to a depth limit, shaded by the materials it hits, and averaged over multiple samples per pixel for anti-aliasing.

**Definition of done:** `./build/raytracer --out out/render.png` produces a valid PNG showing at least three spheres (one diffuse, one metal, one glass) resting on a large ground sphere, with visibly smooth (anti-aliased) edges and a blue-to-white sky gradient in the background.

---

## 2. Non-goals

Out of scope for this demo — keep the surface small:

- Triangles, meshes, or model loading
- Textures or image-based materials
- Lights as objects / explicit light sampling (sky gradient is the only light)
- Multithreading (single-threaded is fine and keeps the code readable)
- Motion blur, depth of field beyond a simple aperture, volumes, BVH acceleration
- A GUI or real-time preview

If an agent proposes any of the above, the Orchestrator defers it to a "stretch goals" note and does not let it block the core build.

---

## 3. Constraints

- **Language:** C++17. Header-only modules where practical (keeps the file count and the CMake simple).
- **Dependencies:** standard library only, plus one vendored single-header file, `stb_image_write.h`, in `third_party/`. No package manager, no network at build time.
- **Build:** CMake ≥ 3.16, one `raytracer` executable target plus an optional `tests` target.
- **Platforms:** must build clean on clang, gcc, and MSVC with `-std=c++17` (or `/std:c++17`).
- **Style:** warnings-clean at `-Wall -Wextra`. No raw `new`/`delete`; use `std::shared_ptr` for scene objects and materials.

---

## 4. Module breakdown and interfaces

The interfaces below are **the contracts**. The Orchestrator agent commits these header signatures *before* dispatching specialists, so every agent codes against the same shapes. Changing a signature is a coordination event, not a local decision.

### 4.1 `vec3.hpp` — Math agent

A 3-component double vector, reused as point, direction, and RGB color.

```cpp
class vec3 {
public:
    vec3();
    vec3(double x, double y, double z);

    double x() const; double y() const; double z() const;

    vec3 operator-() const;
    double operator[](int i) const;

    vec3& operator+=(const vec3& v);
    vec3& operator*=(double t);
    vec3& operator/=(double t);

    double length() const;
    double length_squared() const;
    bool near_zero() const;                 // true if all components ~0

    static vec3 random();                   // components in [0,1)
    static vec3 random(double min, double max);
};

using point3 = vec3;   // a position
using color  = vec3;   // an RGB triple in [0,1]

// free functions
vec3   operator+(const vec3&, const vec3&);
vec3   operator-(const vec3&, const vec3&);
vec3   operator*(const vec3&, const vec3&);
vec3   operator*(double, const vec3&);
vec3   operator*(const vec3&, double);
vec3   operator/(const vec3&, double);
double dot(const vec3&, const vec3&);
vec3   cross(const vec3&, const vec3&);
vec3   unit_vector(const vec3&);
vec3   random_unit_vector();
vec3   random_in_unit_sphere();
vec3   reflect(const vec3& v, const vec3& n);
vec3   refract(const vec3& uv, const vec3& n, double etai_over_etat);
```

### 4.2 `ray.hpp` — Math agent

```cpp
class ray {
public:
    ray();
    ray(const point3& origin, const vec3& direction);
    const point3& origin() const;
    const vec3&   direction() const;
    point3 at(double t) const;              // origin + t*direction
};
```

### 4.3 `hittable.hpp` — Geometry agent

The intersection contract that geometry and materials both depend on.

```cpp
class material;                             // fwd decl

struct hit_record {
    point3 p;                               // hit point
    vec3   normal;                          // unit, faces against the ray
    std::shared_ptr<material> mat;
    double t;
    bool   front_face;
    void set_face_normal(const ray& r, const vec3& outward_normal);
};

class hittable {
public:
    virtual ~hittable() = default;
    virtual bool hit(const ray& r, double t_min, double t_max,
                     hit_record& rec) const = 0;
};
```

### 4.4 `sphere.hpp` — Geometry agent

```cpp
class sphere : public hittable {
public:
    sphere(point3 center, double radius, std::shared_ptr<material> mat);
    bool hit(const ray& r, double t_min, double t_max,
             hit_record& rec) const override;
};
```

### 4.5 `hittable_list.hpp` — Geometry agent

```cpp
class hittable_list : public hittable {
public:
    hittable_list();
    void clear();
    void add(std::shared_ptr<hittable> object);
    bool hit(const ray& r, double t_min, double t_max,
             hit_record& rec) const override;   // nearest hit wins
};
```

### 4.6 `material.hpp` — Rendering agent

```cpp
class material {
public:
    virtual ~material() = default;
    // returns false if the ray is absorbed
    virtual bool scatter(const ray& r_in, const hit_record& rec,
                         color& attenuation, ray& scattered) const = 0;
};

class lambertian : public material {        // diffuse
public: explicit lambertian(const color& albedo); /* ... */ };

class metal : public material {             // reflective, fuzz in [0,1]
public: metal(const color& albedo, double fuzz); /* ... */ };

class dielectric : public material {        // glass, index of refraction
public: explicit dielectric(double index_of_refraction); /* ... */ };
```

### 4.7 `camera.hpp` — Rendering agent

```cpp
class camera {
public:
    camera(point3 lookfrom, point3 lookat, vec3 vup,
           double vfov_degrees, double aspect_ratio);
    ray get_ray(double s, double t) const;  // s,t in [0,1] across the image
};
```

### 4.8 `color.hpp` — I/O agent

```cpp
// Converts an accumulated color (summed over samples_per_pixel) to
// gamma-corrected 8-bit RGB and appends it to the pixel buffer.
void write_color(std::vector<unsigned char>& buffer,
                 color pixel_color, int samples_per_pixel);
```

### 4.9 `image_writer.hpp` — I/O agent

```cpp
// PPM path: plain-text P3, always available, zero deps.
bool write_ppm(const std::string& path, int width, int height,
               const std::vector<unsigned char>& rgb);

// PNG path: wraps stbi_write_png from third_party/stb_image_write.h.
bool write_png(const std::string& path, int width, int height,
               const std::vector<unsigned char>& rgb);

// Dispatches on file extension (.png vs .ppm).
bool write_image(const std::string& path, int width, int height,
                 const std::vector<unsigned char>& rgb);
```

### 4.10 `main.cpp` — Orchestrator + Rendering agent

Owns: CLI parsing, scene construction, the render loop, the `ray_color` recursion, progress reporting, and the call to `write_image`.

```cpp
// core recursion — lives in main.cpp or a ray_color.hpp
color ray_color(const ray& r, const hittable& world, int depth);

int main(int argc, char** argv);
```

---

## 5. CLI

```
raytracer [options]

  --width   N     image width in pixels        (default 400)
  --samples N     samples per pixel (AA)        (default 32)
  --depth   N     max bounces per ray           (default 16)
  --out     PATH  output file, .png or .ppm     (default out/render.png)
  --scene   NAME  "default" | "three-spheres"   (default "three-spheres")
  --help          print usage and exit
```

Aspect ratio is fixed at 16:9; height is derived from width. Unknown flags print usage and exit non-zero.

---

## 6. Rendering algorithm (reference)

For each pixel `(i, j)`:

1. Accumulate `color pixel = (0,0,0)`.
2. Repeat `samples` times: jitter the pixel by a random offset in `[0,1)²`, build `s,t`, get a ray from the camera, add `ray_color(ray, world, depth)`.
3. `write_color(buffer, pixel, samples)` — this divides by sample count, applies gamma-2 (`sqrt`), and clamps to `[0,255]`.

`ray_color(r, world, depth)`:

- If `depth <= 0` return black.
- If `world.hit(r, 0.001, +inf, rec)`:
  - if `rec.mat->scatter(...)` returns a scattered ray, return `attenuation * ray_color(scattered, world, depth-1)`;
  - else return black (absorbed).
- Otherwise return the sky: lerp white→light-blue by the ray's y direction.

The `0.001` `t_min` is the shadow-acne fix — a classic "why is my image speckled" teaching moment if an agent forgets it.

---

## 7. Default scene (`three-spheres`)

- Ground: sphere at `(0, -100.5, -1)`, radius `100`, `lambertian` albedo `(0.8, 0.8, 0.0)`.
- Center: sphere at `(0, 0, -1)`, radius `0.5`, `lambertian` albedo `(0.1, 0.2, 0.5)`.
- Left: sphere at `(-1, 0, -1)`, radius `0.5`, `dielectric` IOR `1.5`.
- Right: sphere at `(1, 0, -1)`, radius `0.5`, `metal` albedo `(0.8, 0.6, 0.2)`, fuzz `0.0`.
- Camera: `lookfrom (0,0,0)`, `lookat (0,0,-1)`, `vup (0,1,0)`, vfov `90°`.

This is the image the demo aims for.

---

## 8. Acceptance criteria

QA checks these before the build is declared done:

1. **Builds clean:** `cmake --build build` succeeds with `-Wall -Wextra`, no warnings.
2. **Runs:** default invocation exits `0` and writes a non-empty output file.
3. **Valid image:** output PNG opens in a standard viewer; dimensions match `--width` and derived height.
4. **Visually correct:** three foreground spheres + ground visible; sky gradient present; edges anti-aliased (no hard jaggies at `--samples 32`).
5. **Materials behave:** metal sphere shows reflections; glass sphere refracts/inverts the scene behind it.
6. **CLI honored:** `--width`, `--samples`, `--out` all take effect; `--help` and unknown flags behave as specified.
7. **Unit tests pass:** the `tests` target is green (see §9).

---

## 9. Unit tests (QA agent)

Lightweight assertions, no framework required (a tiny `assert`-based harness is fine):

- **vec3:** dot product of orthogonal vectors is 0; `length` of `(3,4,0)` is `5`; `reflect` of a vector off a flat normal negates the normal component; `unit_vector` has length ≈ 1.
- **ray:** `at(t)` returns `origin + t*direction`.
- **sphere:** a ray straight at a unit sphere at `(0,0,-1)` hits at the expected `t`; a ray pointing away misses.
- **hittable_list:** with two overlapping spheres, `hit` returns the nearer `t`.
- **color:** `write_color` gamma-corrects and clamps (e.g. an over-bright sample clamps to 255, not wraps).

---

## 10. Stretch goals (only if time remains, never blocking)

- `--threads N` with `std::thread` tiling of the image.
- Defocus blur (aperture + focus distance) on the camera.
- A random "many spheres" scene like the RTIOW cover image.
- Progress bar to `stderr` with ETA.

These are explicitly the Orchestrator's overflow bucket — good material for a "what would you delegate next?" audience question.
