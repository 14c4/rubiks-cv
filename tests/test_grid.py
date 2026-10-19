import numpy as np

from cubetrack.vision.grid import GuideGrid, bgr_means_to_lab8, uneven_cells


def test_centered_grid_matches_the_spike_layout_on_640x480():
    assert GuideGrid.centered(640, 480) == GuideGrid(x=200, y=120, cell=80, margin=20)


def test_each_cell_samples_only_its_own_interior():
    grid = GuideGrid(x=0, y=0, cell=10, margin=2)
    frame = np.zeros((30, 30, 3), np.uint8)
    frame[10:20, 20:30] = (0, 0, 255)  # cell (1, 2) red
    frame[0:10, 0:10] = (255, 255, 255)  # cell (0, 0) white ...
    frame[0:2, 0:10] = (0, 0, 0)  # ... except a dark band inside the margin, which must be ignored
    means = grid.sample_bgr(frame)
    assert means[1, 2].tolist() == [0, 0, 255]
    assert means[0, 0].tolist() == [255, 255, 255]
    assert means[2, 2].tolist() == [0, 0, 0]


def test_spread_flags_a_box_straddling_two_colors():
    grid = GuideGrid(x=0, y=0, cell=20, margin=5)
    frame = np.zeros((60, 60, 3), np.uint8)
    frame[:, :] = (0, 0, 200)  # all red ...
    frame[0:20, 10:20] = (255, 255, 255)  # ... except cell (0, 0), whose box is half white
    means, spread = grid.sample(frame)
    flags = uneven_cells(spread)
    assert flags[0] and not flags[1:].any()


def test_center_is_never_flagged_uneven_by_default():
    spread = np.full((3, 3), 50.0)
    assert not uneven_cells(spread)[4]
    assert uneven_cells(spread, skip_center=False)[4]


def test_moved_and_resized_grid_stays_centered_on_the_same_point():
    grid = GuideGrid(200, 120, 80, 20)
    bigger = grid.moved(dcell=2)
    assert (bigger.cell, bigger.margin) == (82, 20)
    assert bigger.x + 3 * bigger.cell / 2 == grid.x + 3 * grid.cell / 2
    assert grid.moved(dx=5, dy=-5) == GuideGrid(205, 115, 80, 20)
    assert not GuideGrid(600, 0, 80, 20).fits(640, 480)


def test_lab_conversion_keeps_shape_and_matches_known_values():
    lab = bgr_means_to_lab8(np.array([[[255.0, 255.0, 255.0], [0.0, 0.0, 255.0]]]))
    assert lab.shape == (1, 2, 3)
    assert lab[0, 0].tolist() == [255, 128, 128]  # white: full lightness, neutral a and b
    assert lab[0, 1].tolist() == [136, 208, 195]  # pure red, as measured in Milestone 0.3
