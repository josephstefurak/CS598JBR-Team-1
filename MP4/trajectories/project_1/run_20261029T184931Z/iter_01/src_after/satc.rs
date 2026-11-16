//! A safe Rust translation of the header-only `satc` collision library.
//!
//! The C library mutates points through `double *`; the interface here returns
//! freshly computed points instead, but keeps the C order of operations so the
//! results are bit-identical.

/// A circle shape, with a position and radius.
#[derive(Debug, Clone)]
pub struct SatcCircle {
    /// The position of the circle.
    pub pos: [f64; 2],
    /// The radius of the circle.
    pub r: f64,
}

/// A polygon shape, with a position, angle, offset, and points.
#[derive(Debug, Clone)]
pub struct SatcPolygon {
    /// The position of the polygon.
    pub pos: [f64; 2],
    /// The number of points in the polygon.
    pub num_points: usize,
    /// The points of the polygon.
    pub points: Vec<[f64; 2]>,
    /// The angle of rotation of the polygon.
    pub angle: f64,
    /// The offset of the polygon.
    pub offset: [f64; 2],
    /// The calculated points of the polygon. Derived; do not modify directly.
    pub calc_points: Vec<[f64; 2]>,
    /// The calculated edges of the polygon. Derived; do not modify directly.
    pub edges: Vec<[f64; 2]>,
    /// The calculated normals of the polygon. Derived; do not modify directly.
    pub normals: Vec<[f64; 2]>,
}

/// A box shape, with a position, width, and height.
#[derive(Debug, Clone)]
pub struct SatcBox {
    /// The position of the box, from the top left.
    pub pos: [f64; 2],
    /// The width of the box.
    pub w: f64,
    /// The height of the box.
    pub h: f64,
}

/// A response, representing an overlap between two shapes.
#[derive(Debug, Clone)]
pub struct SatcResponse {
    /// The length of overlap of the collision.
    pub overlap: f64,
    /// The unit vector of the overlap of the collision.
    pub overlap_n: [f64; 2],
    /// The overlap unit vector, scaled by the length of the overlap.
    pub overlap_v: [f64; 2],
    /// True if shape `a` is entirely within shape `b`.
    pub a_in_b: bool,
    /// True if shape `b` is entirely within shape `a`.
    pub b_in_a: bool,
}

/// Denotes an undefined shape type.
pub const SATC_TYPE_NONE: i32 = 0;
/// Denotes a circle shape type.
pub const SATC_TYPE_CIRCLE: i32 = 1;
/// Denotes a polygon shape type.
pub const SATC_TYPE_POLYGON: i32 = 2;
/// Denotes a box shape type.
pub const SATC_TYPE_BOX: i32 = 3;
/// Denotes a left voronoi region, for polygon collision detection.
pub const SATC_LEFT_VORONOI_REGION: i32 = -1;
/// Denotes a middle voronoi region, for polygon collision detection.
pub const SATC_MIDDLE_VORONOI_REGION: i32 = 0;
/// Denotes a right voronoi region, for polygon collision detection.
pub const SATC_RIGHT_VORONOI_REGION: i32 = 1;

/// The dot product of two points.
fn point_dot(p: &[f64; 2], q: &[f64; 2]) -> f64 {
    p[0] * q[0] + p[1] * q[1]
}

/// The length, squared, of a point.
fn point_len2(p: &[f64; 2]) -> f64 {
    point_dot(p, p)
}

/// The length of a point.
fn point_len(p: &[f64; 2]) -> f64 {
    point_len2(p).sqrt()
}

impl SatcCircle {
    /// Create a circle with a given position and radius.
    pub fn new(pos: [f64; 2], r: f64) -> Self {
        SatcCircle { pos, r }
    }
}

impl SatcPolygon {
    /// Create a polygon with a given position and points.
    ///
    /// The calculated points, edges and normals are computed immediately.
    pub fn new(pos: [f64; 2], points: Vec<[f64; 2]>) -> Self {
        let mut polygon = SatcPolygon {
            pos,
            num_points: 0,
            points: Vec::new(),
            angle: 0.0,
            offset: [0.0, 0.0],
            calc_points: Vec::new(),
            edges: Vec::new(),
            normals: Vec::new(),
        };
        satc_polygon_set_points(&mut polygon, points);
        polygon
    }
}

impl SatcBox {
    /// Create a box with a given position, width and height.
    pub fn new(pos: [f64; 2], w: f64, h: f64) -> Self {
        SatcBox { pos, w, h }
    }
}

impl SatcResponse {
    /// Create a pristine collision response.
    ///
    /// Instead of setting the values manually, use one of the `satc_test_*`
    /// functions, which set them for you.
    pub fn new() -> Self {
        SatcResponse {
            overlap: f64::MAX,
            overlap_n: [0.0, 0.0],
            overlap_v: [0.0, 0.0],
            a_in_b: true,
            b_in_a: true,
        }
    }
}

impl Default for SatcResponse {
    fn default() -> Self {
        Self::new()
    }
}

/// Recalculate the calculated points, edges and normals of a polygon.
fn polygon_recalc(polygon: &mut SatcPolygon) {
    let offset = polygon.offset;
    let angle = polygon.angle;

    polygon.calc_points = polygon
        .points
        .iter()
        .take(polygon.num_points)
        .map(|point| {
            let calc_point = satc_point_add(point, &offset);
            if angle == 0.0 {
                calc_point
            } else {
                satc_point_rotate(&calc_point, angle)
            }
        })
        .collect();

    let len = polygon.calc_points.len();
    let mut edges = Vec::with_capacity(len);
    let mut normals = Vec::with_capacity(len);
    for (i, p1) in polygon.calc_points.iter().enumerate() {
        let p2 = polygon.calc_points[(i + 1) % len];
        let edge = satc_point_sub(&p2, p1);
        normals.push(satc_point_normalize(&satc_point_perp(&edge)));
        edges.push(edge);
    }

    polygon.edges = edges;
    polygon.normals = normals;
}

/// Replace a polygon's points and recalculate all of its derived values.
pub fn satc_polygon_set_points(polygon: &mut SatcPolygon, points: Vec<[f64; 2]>) {
    polygon.num_points = points.len();
    polygon.points = points;
    polygon_recalc(polygon);
}

/// Create a box shape.
pub fn satc_box_create(pos: [f64; 2], w: f64, h: f64) -> SatcBox {
    SatcBox::new(pos, w, h)
}

/// Return a polygon representing the box.
pub fn satc_box_to_polygon(box_: &SatcBox) -> SatcPolygon {
    let w = box_.w;
    let h = box_.h;
    SatcPolygon::new(box_.pos, vec![[0.0, 0.0], [w, 0.0], [w, h], [0.0, h]])
}

/// Check whether two polygons are overlapping.
pub fn satc_test_polygon_polygon(
    a: &SatcPolygon,
    b: &SatcPolygon,
    response: &mut SatcResponse,
) -> bool {
    let a_len = a.num_points;
    let b_len = b.num_points;

    for axis in a.normals.iter().chain(b.normals.iter()) {
        if satc_is_separating_axis(
            &a.pos, &b.pos, a_len, &a.points, b_len, &b.points, axis, response,
        ) {
            return false;
        }
    }

    response.overlap_v = satc_point_scale_x(&response.overlap_n, response.overlap);
    true
}

/// Copy the values of the point `q` onto the point `p`.
///
/// The C function mutates `p` in place and returns it.
pub fn satc_point_copy(p: &[f64; 2], q: &[f64; 2]) -> [f64; 2] {
    let mut p = *p;
    p[0] = q[0];
    p[1] = q[1];
    p
}

/// Return the point perpendicular to `p`.
pub fn satc_point_perp(p: &[f64; 2]) -> [f64; 2] {
    [p[1], -p[0]]
}

/// Return the inverse of the point `p`.
pub fn satc_point_reverse(p: &[f64; 2]) -> [f64; 2] {
    [-p[0], -p[1]]
}

/// Return the sum of two points.
pub fn satc_point_add(p: &[f64; 2], q: &[f64; 2]) -> [f64; 2] {
    [p[0] + q[0], p[1] + q[1]]
}

/// Return the difference of two points.
pub fn satc_point_sub(p: &[f64; 2], q: &[f64; 2]) -> [f64; 2] {
    [p[0] - q[0], p[1] - q[1]]
}

/// Scale a point by `x` horizontally and `y` vertically.
pub fn satc_point_scale_xy(p: &[f64; 2], x: f64, y: f64) -> [f64; 2] {
    [p[0] * x, p[1] * y]
}

/// Scale a point by `x` along both axes.
pub fn satc_point_scale_x(p: &[f64; 2], x: f64) -> [f64; 2] {
    satc_point_scale_xy(p, x, x)
}

/// Create a point from an `x` and a `y` value.
pub fn satc_point_create(x: f64, y: f64) -> [f64; 2] {
    [x, y]
}

/// Rotate a point by some angle.
///
/// The C computes the new `y` as `x * sin(angle) - y * cos(angle)`, which is a
/// sign error; it is reproduced here exactly.
pub fn satc_point_rotate(p: &[f64; 2], angle: f64) -> [f64; 2] {
    let x = p[0];
    let y = p[1];
    [
        x * angle.cos() - y * angle.sin(),
        x * angle.sin() - y * angle.cos(),
    ]
}

/// Normalize a point into a unit vector.
pub fn satc_point_normalize(p: &[f64; 2]) -> [f64; 2] {
    let d = point_len(p);
    if d > 0.0 { [p[0] / d, p[1] / d] } else { *p }
}

/// Project the point `q` onto `p`.
pub fn satc_point_project(p: &[f64; 2], q: &[f64; 2]) -> [f64; 2] {
    let amt = point_dot(p, q) / point_len2(q);
    [amt * p[0], amt * p[1]]
}

/// Reflect a point along some axis.
pub fn satc_point_reflect(p: &[f64; 2], axis: &[f64; 2]) -> [f64; 2] {
    let x = p[0];
    let y = p[1];
    let projected = satc_point_scale_x(&satc_point_project(p, axis), 2.0);
    [projected[0] - x, projected[1] - y]
}

/// Create a circle with a given position and radius.
pub fn satc_circle_create(pos: [f64; 2], r: f64) -> SatcCircle {
    SatcCircle::new(pos, r)
}

/// Return a rectangular polygon equivalent to the bounding box of a circle.
pub fn satc_circle_get_aabb(circle: &SatcCircle) -> SatcPolygon {
    let r = circle.r;
    let corner = [circle.pos[0] - r, circle.pos[1] - r];
    satc_box_to_polygon(&satc_box_create(corner, r * 2.0, r * 2.0))
}

/// Create a polygon with a given position and points.
pub fn satc_polygon_create(pos: [f64; 2], points: Vec<[f64; 2]>) -> SatcPolygon {
    SatcPolygon::new(pos, points)
}

/// Return a polygon representing the bounding box of a polygon.
///
/// The C initialises `y_max` from `x_max` rather than from `y_min`, and adds
/// the lower bounds to an uninitialised stack point. Both are reproduced here,
/// with the uninitialised point taken to be the origin.
pub fn satc_polygon_get_aabb(polygon: &SatcPolygon) -> SatcPolygon {
    let first = polygon.points.first().copied().unwrap_or([0.0, 0.0]);
    let mut x_min = first[0];
    let mut y_min = first[1];
    let mut x_max = x_min;
    let mut y_max = x_max;
    for point in polygon.points.iter().take(polygon.num_points).skip(1) {
        let x = point[0];
        let y = point[1];
        if x < x_min {
            x_min = x;
        }
        if x > x_max {
            x_max = x;
        }
        if y < y_min {
            y_min = y;
        }
        if y > y_max {
            y_max = y;
        }
    }

    let pos = [x_min, y_min];
    satc_box_to_polygon(&satc_box_create(pos, x_max - x_min, y_max - y_min))
}

/// Get the "centroid" (the estimated center) of a polygon.
pub fn satc_polygon_get_centroid(polygon: &SatcPolygon) -> [f64; 2] {
    let points = &polygon.calc_points;
    let len = points.len();
    let mut cx = 0.0;
    let mut cy = 0.0;
    let mut ar = 0.0;
    for (i, p1) in points.iter().enumerate() {
        let p2 = points[(i + 1) % len];
        let a = p1[0] * p2[1] - p2[0] * p1[1];
        cx += (p1[0] + p2[0]) * a;
        cy += (p1[1] + p2[1]) * a;
        ar += a;
    }

    ar *= 3.0;
    satc_point_create(cx / ar, cy / ar)
}

/// Create a pristine collision response.
pub fn satc_response_create() -> SatcResponse {
    SatcResponse::new()
}

/// Project the first `len` points onto an axis, as a `[min, max]` range.
pub fn satc_flatten_points_on(
    len: usize,
    points: &[[f64; 2]],
    normal: &[f64; 2],
    result: &mut [f64; 2],
) {
    let mut min = f64::MAX;
    let mut max = -f64::MAX;

    for point in points.iter().take(len) {
        let dot = point_dot(point, normal);
        if dot < min {
            min = dot;
        }
        if dot > max {
            max = dot;
        }
    }

    result[0] = min;
    result[1] = max;
}

/// Figure out whether two sets of points are separated along a given axis.
///
/// Primarily meant for internal use.
#[allow(clippy::too_many_arguments)]
pub fn satc_is_separating_axis(
    a_pos: &[f64; 2],
    b_pos: &[f64; 2],
    a_len: usize,
    a_points: &[[f64; 2]],
    b_len: usize,
    b_points: &[[f64; 2]],
    axis: &[f64; 2],
    response: &mut SatcResponse,
) -> bool {
    // The magnitude of the offset between the two polygons.
    let offset_v = satc_point_sub(b_pos, a_pos);
    let projected_offset = point_dot(&offset_v, axis);
    // Project the polygons onto the axis.
    let mut range_a = [0.0, 0.0];
    let mut range_b = [0.0, 0.0];
    satc_flatten_points_on(a_len, a_points, axis, &mut range_a);
    satc_flatten_points_on(b_len, b_points, axis, &mut range_b);
    // Move B's range to its position relative to A.
    range_b[0] += projected_offset;
    range_b[1] += projected_offset;
    // Check if there is a gap. If there is, this is a separating axis.
    if range_a[0] > range_b[1] || range_b[0] > range_a[1] {
        return true;
    }

    // Pick the shortest way out when one range is fully inside the other.
    let shortest_way_out = || {
        let option_1 = range_a[1] - range_b[0];
        let option_2 = range_b[1] - range_a[0];
        if option_1 < option_2 { option_1 } else { -option_2 }
    };

    // This is not a separating axis, so calculate the overlap.
    let overlap = if range_a[0] < range_b[0] {
        // A starts further left than B.
        response.a_in_b = false;
        if range_a[1] < range_b[1] {
            // A ends before B does. We have to pull A out of B.
            response.b_in_a = false;
            range_a[1] - range_b[1]
        } else {
            // B is fully inside A.
            shortest_way_out()
        }
    } else {
        // B starts further left than A.
        response.b_in_a = false;
        if range_a[1] > range_b[1] {
            // B ends before A ends. We have to push A out of B.
            response.a_in_b = false;
            range_a[0] - range_b[1]
        } else {
            // A is fully inside B.
            shortest_way_out()
        }
    };

    // If this is the smallest overlap so far, set it as the minimum overlap.
    let abs_overlap = overlap.abs();
    if abs_overlap < response.overlap {
        response.overlap = abs_overlap;
        response.overlap_n = if overlap < 0.0 {
            satc_point_reverse(axis)
        } else {
            *axis
        };
    }

    false
}

/// Figure out whether a point lies in the left, middle or right voronoi region
/// of a line.
pub fn satc_voronoi_region(line: &[f64; 2], point: &[f64; 2]) -> i32 {
    let len_2 = point_len2(line);
    let dp = point_dot(point, line);
    // If the point is beyond the start of the line, it is in the left region.
    if dp < 0.0 {
        SATC_LEFT_VORONOI_REGION
    // If the point is beyond the end of the line, it is in the right region.
    } else if dp > len_2 {
        SATC_RIGHT_VORONOI_REGION
    } else {
        SATC_MIDDLE_VORONOI_REGION
    }
}

/// Returns true if a point is inside of a circle.
pub fn satc_point_in_circle(point: &[f64; 2], circle: &SatcCircle) -> bool {
    let difference_v = satc_point_sub(point, &circle.pos);
    let radius_sq = circle.r * circle.r;
    point_len2(&difference_v) <= radius_sq
}

/// Returns true if a point is inside of a polygon.
///
/// As in the C, this collides a very small box polygon with the polygon and
/// reports whether the box ended up entirely inside it.
pub fn satc_point_in_polygon(point: &[f64; 2], polygon: &SatcPolygon) -> bool {
    let mut test_point = satc_box_to_polygon(&satc_box_create([0.0, 0.0], 0.000001, 0.000001));
    test_point.pos = *point;
    let mut response = satc_response_create();

    satc_test_polygon_polygon(&test_point, polygon, &mut response) && response.a_in_b
}

/// Returns true if a circle overlaps with another circle.
pub fn satc_test_circle_circle(a: &SatcCircle, b: &SatcCircle, response: &mut SatcResponse) -> bool {
    let difference_v = satc_point_sub(&b.pos, &a.pos);
    let total_radius = a.r + b.r;
    let total_radius_sq = total_radius * total_radius;
    let distance_sq = point_len2(&difference_v);
    if distance_sq > total_radius_sq {
        return false;
    }

    let distance = distance_sq.sqrt();
    response.overlap = total_radius - distance;
    response.overlap_n = satc_point_normalize(&difference_v);
    response.overlap_v = satc_point_scale_x(&response.overlap_n, response.overlap);
    response.a_in_b = (a.r <= b.r) && (distance <= b.r - a.r);
    response.b_in_a = (b.r <= a.r) && (distance <= a.r - b.r);
    true
}

/// Checks whether a polygon and a circle are overlapping.
pub fn satc_test_polygon_circle(
    polygon: &SatcPolygon,
    circle: &SatcCircle,
    response: &mut SatcResponse,
) -> bool {
    let circle_pos = satc_point_sub(&circle.pos, &polygon.pos);
    let radius = circle.r;
    let radius2 = radius * radius;
    let points = &polygon.calc_points;
    let len = points.len();

    for i in 0..len {
        let next = (i + 1) % len;
        let prev = (i + len - 1) % len;
        let mut overlap = 0.0;
        let mut overlap_n = None;

        let edge = polygon.edges[i];
        let point = satc_point_sub(&circle_pos, &points[i]);

        if point_len2(&point) > radius2 {
            response.a_in_b = false;
        }

        match satc_voronoi_region(&edge, &point) {
            SATC_LEFT_VORONOI_REGION => {
                let prev_edge = polygon.edges[prev];
                let prev_point = satc_point_sub(&circle_pos, &points[prev]);
                if satc_voronoi_region(&prev_edge, &prev_point) == SATC_RIGHT_VORONOI_REGION {
                    let dist = point_len(&point);
                    if dist > radius {
                        return false;
                    }
                    response.b_in_a = false;
                    overlap_n = Some(satc_point_normalize(&point));
                    overlap = radius - dist;
                }
            }
            SATC_RIGHT_VORONOI_REGION => {
                let next_edge = polygon.edges[next];
                let next_point = satc_point_sub(&circle_pos, &points[next]);
                if satc_voronoi_region(&next_edge, &next_point) == SATC_LEFT_VORONOI_REGION {
                    let dist = point_len(&next_point);
                    if dist > radius {
                        return false;
                    }
                    response.b_in_a = false;
                    overlap_n = Some(satc_point_normalize(&next_point));
                    overlap = radius - dist;
                }
            }
            _ => {
                let normal = satc_point_normalize(&satc_point_perp(&edge));
                let dist = point_dot(&point, &normal);
                if dist > 0.0 && dist.abs() > radius {
                    return false;
                }
                overlap_n = Some(normal);
                overlap = radius - dist;
                if dist >= 0.0 || overlap < 2.0 * radius {
                    response.b_in_a = false;
                }
            }
        }

        match overlap_n {
            Some(normal) if overlap.abs() < response.overlap.abs() => {
                response.overlap = overlap;
                response.overlap_n = normal;
            }
            _ => {}
        }
    }

    response.overlap_v = satc_point_scale_x(&response.overlap_n, response.overlap);
    true
}

/// Checks whether a circle and a polygon are overlapping.
///
/// This is slightly more expensive than `satc_test_polygon_circle`, since the
/// response data needs to be flipped after checking the collision.
pub fn satc_test_circle_polygon(
    circle: &SatcCircle,
    polygon: &SatcPolygon,
    response: &mut SatcResponse,
) -> bool {
    let result = satc_test_polygon_circle(polygon, circle, response);
    if result {
        response.overlap_n = satc_point_reverse(&response.overlap_n);
        response.overlap_v = satc_point_reverse(&response.overlap_v);
        std::mem::swap(&mut response.a_in_b, &mut response.b_in_a);
    }

    result
}
